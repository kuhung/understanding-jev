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

function normalizeStats(data, generationId) {
  const totalMs = toMs(data.latency);
  const computeMs = toMs(data.generation_time);
  const cost = toFinite(data.total_cost != null ? data.total_cost : data.usage);
  const promptTokens = toFinite(
    data.native_tokens_prompt != null ? data.native_tokens_prompt : data.tokens_prompt
  );
  const completionTokens = toFinite(
    data.native_tokens_completion != null ? data.native_tokens_completion : data.tokens_completion
  );
  const routingMs = (totalMs != null && computeMs != null)
    ? Math.max(0, totalMs - computeMs)
    : null;

  return {
    id: data.id || generationId,
    latency_ms: totalMs,
    generation_ms: computeMs,
    routing_ms: routingMs,
    cost,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    streamed: data.streamed === true
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
      console.log(
        `[OpenRouter generation] id=${generationId} attempt=${attempt}`,
        `latency=${parsed.latency_ms} gen_time=${parsed.generation_ms} cost=${parsed.cost}`
      );
      if (parsed.latency_ms != null && parsed.generation_ms != null) {
        return parsed;
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
  const totalMs = stats ? stats.latency_ms : null;
  const computeMs = stats ? stats.generation_ms : null;
  const routingMs = stats && stats.routing_ms != null
    ? stats.routing_ms
    : (totalMs != null && computeMs != null ? Math.max(0, totalMs - computeMs) : null);
  const promptTokens = (stats && stats.prompt_tokens != null) ? stats.prompt_tokens : tokens.prompt;
  const completionTokens = (stats && stats.completion_tokens != null) ? stats.completion_tokens : tokens.completion;

  return {
    id: (stats && stats.id) || generationId || null,
    latency_ms: totalMs,
    generation_ms: computeMs,
    routing_ms: routingMs,
    cost,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    proxy_ms: proxyTotalMs != null ? proxyTotalMs : proxyTtftMs,
    streamed: stats && stats.streamed != null ? stats.streamed : !!streamed
  };
}
