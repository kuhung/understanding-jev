import fs from 'fs';
import path from 'path';
import { fetchGenerationStats, buildOpenRouterPayload } from '../lib/openrouter-stats.js';

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
  const apiKey = process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY || clientKey || bearerKey;

  if (!apiKey) {
    return res.status(200).json({ success: false, reason: 'No API Key' });
  }

  const body = req.body || {};
  const generationId = body.id || body.generation_id;
  if (!generationId || typeof generationId !== 'string') {
    return res.status(400).json({ success: false, error: 'Missing generation id' });
  }

  const stats = await fetchGenerationStats(apiKey, generationId);
  const openrouter = buildOpenRouterPayload({
    stats,
    usage: body.usage || null,
    proxyTtftMs: body.proxy_ttft,
    proxyTotalMs: body.proxy_total,
    streamed: body.streamed === true,
    generationId
  });

  return res.status(200).json({
    success: !!(stats || openrouter.cost != null),
    openrouter
  });
}
