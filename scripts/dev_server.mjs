// scripts/dev_server.mjs
// Lightweight zero-dependency local dev server for testing static site + /api/decide endpoint.

import http from 'http';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import decideHandler from '../api/decide.js';
import llmHandler from '../api/llm.js';
import generationHandler from '../api/generation.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT_DIR = path.resolve(__dirname, '..');
const PORT = process.env.PORT || 3000;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.mjs': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer(async (req, res) => {
  const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsedUrl.pathname;

  // Handle API routing
  if (pathname === '/api/decide' || pathname === '/api/llm' || pathname === '/api/generation') {
    const handlerFn = pathname === '/api/llm'
      ? llmHandler
      : (pathname === '/api/generation' ? generationHandler : decideHandler);
    let body = '';
    req.on('data', chunk => {
      body += chunk;
      if (body.length > 1e6) req.socket.destroy();
    });

    req.on('end', async () => {
      try {
        req.body = body ? JSON.parse(body) : {};
      } catch (e) {
        req.body = {};
      }

      // Mock Vercel response helpers
      res.status = function(code) {
        res.statusCode = code;
        return res;
      };
      res.json = function(data) {
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify(data));
        return res;
      };

      try {
        await handlerFn(req, res);
      } catch (err) {
        console.error(`[API Error ${pathname}]`, err);
        if (!res.headersSent) {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: err.message, mode: 'fallback' }));
        } else {
          res.end();
        }
      }
    });
    return;
  }

  // Handle Static File Serving
  let filePath = pathname === '/' ? '/index.html' : pathname;
  let absPath = path.join(ROOT_DIR, filePath);

  if (!fs.existsSync(absPath) || fs.statSync(absPath).isDirectory()) {
    absPath = path.join(ROOT_DIR, 'index.html');
  }

  const ext = path.extname(absPath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(absPath, (err, data) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(data);
  });
});

server.listen(PORT, () => {
  const hasKey = !!(process.env.OPENROUTER_API_KEY || process.env.TYPESAFE_API_KEY);
  console.log(`\n==================================================`);
  console.log(`  Jev Playbook Local Server running at:`);
  console.log(`  ➜ http://localhost:${PORT}`);
  console.log(`  ➜ API Endpoint: http://localhost:${PORT}/api/decide`);
  console.log(`  ➜ OPENROUTER_API_KEY: ${hasKey ? '✓ Active' : '✗ Not detected in env (using Trace Fallback or browser input)'}`);
  console.log(`==================================================\n`);
});
