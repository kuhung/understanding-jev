const OR_HEADERS = {
  'HTTP-Referer': 'https://github.com/kuhung/understanding-jev',
  'X-OpenRouter-Title': 'Understanding Jev Interactive Bench'
};

function toFinite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function toMs(value) {
  const n = toFinite(value);
  if (n == null || n < 0) return null;
  return Math.round(n);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function costFromUsage(usage) {
  if (usage == null) return null;
  if (typeof usage === 'number') return usage >= 0 ? usage : null;
  if (typeof usage !== 'object') return null;
  const direct = toFinite(usage.cost);
  if (direct != null && direct >= 0) return direct;
  const total = toFinite(usage.total_cost);
  if (total != null && total >= 0) return total;
  return null;
}

export function tokensFromUsage(usage) {
  if (!usage || typeof usage !== 'object') {
    return { prompt: null, completion: null };
  }
  return {
    prompt: toFinite(usage.prompt_tokens ?? usage.tokens_prompt ?? usage.native_tokens_prompt),
    completion: toFinite(usage.completion_tokens ?? usage.tokens_completion ?? usage.native_tokens_completion)
  };
}

function providerMsFromChain(data) {
  const chain = data && Array.isArray(data.provider_responses) ? data.provider_responses : [];
  for (let i = chain.length - 1; i >= 0; i -= 1) {
    const item = chain[i];
    if (!item || (item.status != null && Number(item.status) !== 200)) continue;
    const ms = toMs(item.latency);
    if (ms != null && ms > 0) return ms;
  }
  return null;
}

function durationFromTimestamps(data) {
  const start = data && (data.started_at || data.startedAt);
  const end = data && (data.finished_at || data.completed_at || data.ended_at || data.finishedAt || data.completedAt);
  if (!start || !end) return null;
  const ms = Date.parse(end) - Date.parse(start);
  return (Number.isFinite(ms) && ms > 0 && ms < 60000) ? Math.round(ms) : null;
}

function toPositiveMs(value) {
  const ms = toMs(value);
  return (ms != null && ms > 0) ? ms : null;
}

function normalizeStats(data, generationId) {
  const streamed = data.streamed === true;
  const apiLatency = toPositiveMs(data.latency);
  const generationMs = toPositiveMs(data.generation_time);
  const chainProviderMs = providerMsFromChain(data);
  const providerMs = chainProviderMs || apiLatency;
  const cost = toFinite(data.total_cost != null ? data.total_cost : data.usage);
  const promptTokens = toFinite(
    data.native_tokens_prompt != null ? data.native_tokens_prompt : data.tokens_prompt
  );
  const completionTokens = toFinite(
    data.native_tokens_completion != null ? data.native_tokens_completion : data.tokens_completion
  );

  // Dashboard: non-stream Total = Routing + Provider. Stream Total = Routing + Generation.
  // Public API `latency` is documented as Total, but live Activity cards show it as Provider
  // when generation_time is larger (streaming). Only treat latency as Total when it actually
  // envelopes the compute bar.
  const computeBarMs = streamed ? generationMs : providerMs;
  let totalMs = null;
  let routingMs = null;
  if (apiLatency != null && computeBarMs != null && apiLatency > computeBarMs) {
    totalMs = apiLatency;
    routingMs = apiLatency - computeBarMs;
  } else if (!streamed && chainProviderMs != null && apiLatency != null && apiLatency > chainProviderMs) {
    totalMs = apiLatency;
    routingMs = apiLatency - chainProviderMs;
  } else {
    const stampMs = durationFromTimestamps(data);
    if (stampMs != null && computeBarMs != null && stampMs >= computeBarMs) {
      totalMs = stampMs;
      routingMs = stampMs - computeBarMs;
    }
  }

  const computeMs = streamed ? (generationMs || providerMs) : providerMs;

  const timingKeys = Object.keys(data).filter((key) => /latenc|time|routing|queue|ttft|delay|duration/i.test(key));
  console.log(
    `[OpenRouter generation] id=${data.id || generationId}`,
    `streamed=${streamed} latency=${apiLatency} gen=${generationMs} chain=${chainProviderMs}`,
    `hero=${computeMs} routing=${routingMs} total=${totalMs}`,
    `timingKeys=${timingKeys.join(',')} keys=${Object.keys(data).join(',')}`
  );

  return {
    id: data.id || generationId,
    provider_ms: providerMs,
    generation_ms: generationMs,
    compute_ms: computeMs,
    latency_ms: apiLatency,
    routing_ms: routingMs,
    total_ms: totalMs,
    cost,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    streamed
  };
}

export async function fetchGenerationStats(apiKey, generationId, { retries = 1, delayMs = 0 } = {}) {
  if (!apiKey || !generationId) return null;
  let lastPartial = null;

  for (let attempt = 0; attempt < retries; attempt += 1) {
    if (attempt > 0 && delayMs > 0) await sleep(delayMs);
    try {
      const res = await fetch(
        `https://openrouter.ai/api/v1/generation?id=${encodeURIComponent(generationId)}`,
        {
          headers: {
            Authorization: `Bearer ${apiKey}`,
            ...OR_HEADERS
          }
        }
      );
      if (res.status === 404) {
        console.warn(`[OpenRouter generation 404] id=${generationId} attempt=${attempt}`);
        continue;
      }
      if (!res.ok) {
        const errText = await res.text();
        console.warn(`[OpenRouter generation ${res.status}]`, errText.slice(0, 240));
        continue;
      }
      const body = await res.json();
      const data = body.data || body;
      if (!data || (data.id == null && data.latency == null && data.total_cost == null)) {
        console.warn(`[OpenRouter generation] empty payload id=${generationId} attempt=${attempt}`);
        continue;
      }

      const parsed = normalizeStats(data, generationId);
      lastPartial = parsed;
      if (parsed.compute_ms != null) {
        if (!parsed.streamed || parsed.generation_ms != null) {
          return parsed;
        }
      }
    } catch (err) {
      console.warn('[OpenRouter generation fetch]', err.message);
    }
  }
  return lastPartial;
}

export function buildOpenRouterPayload({
  stats,
  usage,
  proxyTtftMs,
  proxyTotalMs,
  streamed,
  generationId
}) {
  const tokens = tokensFromUsage(usage);
  const cost = (stats && stats.cost != null) ? stats.cost : costFromUsage(usage);
  const isStreamed = stats && stats.streamed != null ? stats.streamed : !!streamed;
  const providerMs = stats ? stats.provider_ms : null;
  const generationMs = stats ? stats.generation_ms : null;
  const computeMs = stats ? stats.compute_ms : null;
  const totalMs = stats ? stats.total_ms : null;
  const routingMs = stats ? stats.routing_ms : null;
  const promptTokens = (stats && stats.prompt_tokens != null) ? stats.prompt_tokens : tokens.prompt;
  const completionTokens = (stats && stats.completion_tokens != null) ? stats.completion_tokens : tokens.completion;

  return {
    id: (stats && stats.id) || generationId || null,
    provider_ms: providerMs,
    generation_ms: generationMs,
    compute_ms: computeMs,
    latency_ms: stats ? stats.latency_ms : null,
    routing_ms: routingMs,
    total_ms: totalMs,
    cost,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    proxy_ms: proxyTotalMs != null ? proxyTotalMs : proxyTtftMs,
    streamed: isStreamed
  };
}
