import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';

// Flask runs on port 5000 and serves all HTML routes + static CSS.
// This Vite plugin intercepts all non-asset requests and proxies them to Flask.
// Vite's own HMR and module requests pass through untouched.
function flaskProxy() {
  return {
    name: 'flask-proxy',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const url = req.url || '';

        // Skip Vite's own internal requests
        if (url.startsWith('/@') || url.startsWith('/node_modules') ||
            url.startsWith('/src/') || url.includes('hot-update') ||
            url.endsWith('.ts') || url.endsWith('.tsx') ||
            url.endsWith('.js') || url.endsWith('.mjs') ||
            url.endsWith('.jsx') || url.endsWith('.css') ||
            url.endsWith('.json') || url.endsWith('.map')) {
          return next();
        }

        // Proxy everything else to Flask
        try {
          const flaskUrl = `http://127.0.0.1:5000${url}`;
          const headers = { ...req.headers, host: '127.0.0.1:5000' };
          const fetchOpts = {
            method: req.method,
            headers,
          };
          if (req.method !== 'GET' && req.method !== 'HEAD') {
            const chunks = [];
            for await (const chunk of req) chunks.push(chunk);
            fetchOpts.body = Buffer.concat(chunks);
          }

          const flaskRes = await fetch(flaskUrl, fetchOpts);
          const contentType = flaskRes.headers.get('content-type') || 'text/html';
          res.statusCode = flaskRes.status;

          // Forward relevant headers
          for (const [key, val] of flaskRes.headers.entries()) {
            if (!['transfer-encoding', 'connection', 'keep-alive'].includes(key.toLowerCase())) {
              res.setHeader(key, val);
            }
          }

          const body = await flaskRes.arrayBuffer();
          res.end(Buffer.from(body));
        } catch (err) {
          console.error('[flask-proxy] error:', err.message);
          res.statusCode = 502;
          res.end('Flask backend not available. Is app.py running on port 5000?');
        }
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), flaskProxy()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
  server: {
    port: 5173,
    strictPort: true,
  },
});
