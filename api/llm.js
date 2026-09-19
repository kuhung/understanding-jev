import fs from 'fs';
import path from 'path';

function loadEnvFile(filePath) {
  try {
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, 'utf8');
      content.split('\n').forEach(line => {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
          const idx = trimmed.indexOf('=');
          const key = trimmed.slice(0, idx).trim();
          let val = trimmed.slice(idx + 1).trim();
          if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
            val = val.slice(1, -1);
          }
          if (!process.env[key]) {
            process.env[key] = val;
          }
        }
      });
    }
  } catch (e) {}
}

loadEnvFile(path.resolve(process.cwd(), '.env.local'));
loadEnvFile(path.resolve(process.cwd(), '.env'));

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader(
    'Access-Control-Allow-Headers',
    'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version, X-OpenRouter-Key'
  );

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed. Use POST.' });
  }

  const clientKey = req.headers['x-openrouter-key'];
  const authHeader = req.headers['authorization'];
  let bearerKey = '';
  if (authHeader && authHeader.startsWith('Bearer ')) {
    bearerKey = authHeader.slice(7).trim();
  }
  const hasServerKey = !!(process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY);
  const apiKey = process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY || clientKey || bearerKey;

  if (req.body && (req.body.probe === true || req.body.state === 'ping')) {
    return res.status(200).json({
      success: true,
      hasServerKey: hasServerKey,
      hasKey: !!apiKey,
      mode: apiKey ? 'live' : 'fallback'
    });
  }

  if (!apiKey) {
    return res.status(200).json({ mode: 'fallback', hasServerKey: false, reason: 'No API Key' });
  }

  let { state } = req.body || {};
  if (!state || typeof state !== 'string') {
    return res.status(400).json({ error: 'Invalid input' });
  }

  state = state.trim().slice(0, 300);

  const payload = {
    model: 'google/gemini-2.5-flash-lite',
    messages: [
      {
        role: 'system',
        content: 'You are an automated traffic router. Classify the user input into a JSON object: {"threat": boolean, "action": "BLOCK"|"ESCALATE"|"ROUTE_TECH"|"ROUTE_SPAM", "severity": "LOW"|"MEDIUM"|"HIGH"|"CRITICAL", "reason": string}. Respond ONLY with raw compact JSON, no markdown block.'
      },
      {
        role: 'user',
        content: state
      }
    ],
    temperature: 0.1,
    stream: true
  };

  try {
    const upstreamRes = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/kuhung/understanding-jev',
        'X-OpenRouter-Title': 'Understanding Jev Interactive Bench'
      },
      body: JSON.stringify(payload)
    });

    if (!upstreamRes.ok) {
      const err = await upstreamRes.text();
      console.warn(`[Gemini upstream error ${upstreamRes.status}]:`, err);
      return res.status(200).json({ mode: 'fallback', reason: err });
    }

    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive'
    });

    const reader = upstreamRes.body.getReader();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      res.write(value);
    }
    res.end();
  } catch (err) {
    console.error('[Gemini proxy error]:', err);
    if (!res.headersSent) {
      res.status(200).json({ mode: 'fallback', reason: err.message });
    } else {
      res.end();
    }
  }
}
