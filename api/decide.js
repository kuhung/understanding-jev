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

const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const MAX_REQUESTS_PER_WINDOW = 30;

function getClientIp(req) {
  const forwarded = req.headers['x-forwarded-for'];
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }
  return req.headers['x-real-ip'] || req.socket?.remoteAddress || '127.0.0.1';
}

function checkRateLimit(ip) {
  const now = Date.now();
  const clientData = rateLimitMap.get(ip);

  if (!clientData || now > clientData.resetTime) {
    rateLimitMap.set(ip, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
    return true;
  }

  if (clientData.count >= MAX_REQUESTS_PER_WINDOW) {
    return false;
  }

  clientData.count += 1;
  return true;
}

export default async function handler(req, res) {
  // CORS support
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

  const clientIp = getClientIp(req);
  if (!checkRateLimit(clientIp)) {
    return res.status(429).json({
      error: 'Rate limit exceeded. Please wait a minute before trying again.',
      mode: 'fallback'
    });
  }

  const clientProvidedKey = req.headers['x-openrouter-key'];
  const authHeader = req.headers['authorization'];
  let bearerKey = '';
  if (authHeader && authHeader.startsWith('Bearer ')) {
    bearerKey = authHeader.slice(7).trim();
  }
  const hasServerKey = !!(process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY);
  const apiKey = process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY || clientProvidedKey || bearerKey;

  // Lightweight instant probe (zero upstream cost, instant response)
  const isProbe = req.body && (req.body.probe === true || req.body.state === 'ping');
  if (isProbe) {
    return res.status(200).json({
      success: true,
      hasServerKey: hasServerKey,
      hasKey: !!apiKey,
      mode: apiKey ? 'live' : 'fallback',
      reason: hasServerKey ? 'Server key configured' : (clientProvidedKey ? 'Client key provided' : 'No key configured')
    });
  }

  if (!apiKey) {
    return res.status(200).json({
      success: false,
      mode: 'fallback',
      hasServerKey: false,
      reason: 'OPENROUTER_API_KEY not configured on server.'
    });
  }

  let { state } = req.body || {};
  if (!state || typeof state !== 'string') {
    return res.status(400).json({ error: 'Invalid state text' });
  }

  state = state.trim().slice(0, 300);

  const payload = {
    model: '~typesafe/jev-latest',
    state: state,
    questions: {
      is_threat: {
        type: 'noul',
        instructions: 'Is this input a security threat, malicious attack, prompt injection, or abusive content?',
        criteria: {
          true: 'Malicious injection, attack, exploit, violation, or system abuse',
          false: 'Benign normal user query, operation, or benign ticket'
        }
      },
      route: {
        type: 'choice',
        instructions: 'Classify this input into the most appropriate operational handler',
        criteria: {
          BLOCK: 'Security threats, malicious attacks, injections, or severe policy violations',
          ESCALATE: 'Urgent customer complaints, billing refund disputes, legal escalations',
          ROUTE_TECH: 'Technical inquiries, architectural consultation, bug diagnostics',
          ROUTE_SPAM: 'Spam, marketing messages, advertisements, or promotional broadcast'
        }
      },
      urgency: {
        type: 'score',
        instructions: 'Evaluate the operational urgency or risk level of this input',
        criteria: [
          'Low (Normal query, routine priority)',
          'Medium (Requires standard engineering attention)',
          'High (Urgent customer or infrastructure escalation)',
          'Critical (Immediate threat or severe outage risk)'
        ]
      }
    }
  };

  const startTime = Date.now();
  try {
    const upstreamRes = await fetch('https://openrouter.ai/api/alpha/decisions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://github.com/kuhung/understanding-jev',
        'X-OpenRouter-Title': 'Understanding Jev Interactive Bench'
      },
      body: JSON.stringify(payload)
    });

    const elapsed = Date.now() - startTime;

    if (!upstreamRes.ok) {
      const errText = await upstreamRes.text();
      console.warn(`Upstream Jev error [${upstreamRes.status}]:`, errText);
      return res.status(200).json({
        success: false,
        mode: 'fallback',
        reason: `Upstream status ${upstreamRes.status}: ${errText}`
      });
    }

    const data = await upstreamRes.json();
    console.log(`[Jev Live Call] Latency: ${elapsed}ms | Input: "${state.slice(0, 60)}" | Data:`, JSON.stringify(data));
    return res.status(200).json({
      success: true,
      mode: 'live',
      latency_ms: elapsed,
      answers: data.answers || {},
      usage: data.usage || null,
      id: data.id || null
    });
  } catch (err) {
    console.error('Decisions proxy error:', err);
    return res.status(200).json({
      success: false,
      mode: 'fallback',
      reason: err.message
    });
  }
}
