const OR_HEADERS = {
  'HTTP-Referer': 'https://github.com/kuhung/understanding-jev',
  'X-OpenRouter-Title': 'Understanding Jev Interactive Bench'
};

function toFinite(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
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

export function deriveOpenRouterTtft({
  proxyTtftMs,
  proxyTotalMs,
  latencyMs,
  generationMs,
  streamed
}) {
  if (!streamed && generationMs != null) {
    return Math.round(generationMs);
  }
  if (proxyTtftMs == null) return null;
  if (latencyMs == null || generationMs == null || proxyTotalMs == null) {
    return Math.round(proxyTtftMs);
  }
  const overhead = Math.max(0, proxyTotalMs - latencyMs);
  const routing = Math.max(0, latencyMs - generationMs);
  return Math.max(1, Math.round(proxyTtftMs - overhead - routing));
}

export async function fetchGenerationStats(apiKey, generationId, { retries = 6, delayMs = 250 } = {}) {
  if (!apiKey || !generationId) return null;

  for (let attempt = 0; attempt < retries; attempt += 1) {
    if (attempt > 0) await sleep(delayMs);
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
      if (res.status === 404) continue;
      if (!res.ok) {
        const errText = await res.text();
        console.warn(`[OpenRouter generation ${res.status}]`, errText.slice(0, 240));
        continue;
      }
      const body = await res.json();
      const data = body.data || body;
      if (!data || (data.id == null && data.latency == null && data.total_cost == null)) continue;

      const latencyMs = toFinite(data.latency);
      const generationMs = toFinite(data.generation_time);
      const cost = toFinite(data.total_cost != null ? data.total_cost : data.usage);
      const promptTokens = toFinite(
        data.native_tokens_prompt != null ? data.native_tokens_prompt : data.tokens_prompt
      );
      const completionTokens = toFinite(
        data.native_tokens_completion != null ? data.native_tokens_completion : data.tokens_completion
      );

      if (latencyMs == null && generationMs == null && cost == null) continue;

      return {
        id: data.id || generationId,
        latency_ms: latencyMs,
        generation_ms: generationMs,
        cost,
        prompt_tokens: promptTokens,
        completion_tokens: completionTokens
      };
    } catch (err) {
      console.warn('[OpenRouter generation fetch]', err.message);
    }
  }
  return null;
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
  const latencyMs = stats ? stats.latency_ms : null;
  const generationMs = stats ? stats.generation_ms : null;
  const promptTokens = (stats && stats.prompt_tokens != null) ? stats.prompt_tokens : tokens.prompt;
  const completionTokens = (stats && stats.completion_tokens != null) ? stats.completion_tokens : tokens.completion;
  const ttftMs = deriveOpenRouterTtft({
    proxyTtftMs,
    proxyTotalMs,
    latencyMs,
    generationMs,
    streamed
  });

  return {
    id: (stats && stats.id) || generationId || null,
    latency_ms: latencyMs,
    generation_ms: generationMs,
    ttft_ms: ttftMs,
    cost,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    proxy_ms: proxyTotalMs
  };
}
