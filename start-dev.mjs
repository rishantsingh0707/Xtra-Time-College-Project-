// Dev entry point: starts the Flask backend, then launches Vite dev server
// with a proxy so the Bolt preview shows the Python-rendered pages.
import { spawn, execSync } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

// Vite always runs on 5173. Do NOT use process.env.PORT — in this environment
// that's the Anthropic proxy port (9091), not the dev server port.
const VITE_PORT = '5173';
const FLASK_PORT = '5000';

// Kill any stale Flask process on port 5000
try {
  execSync(`pkill -f "python3 app.py" 2>/dev/null || true`, { stdio: 'ignore' });
} catch {}

// Start Flask
const flask = spawn('python3', ['app.py'], {
  stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...process.env, PORT: FLASK_PORT },
});

flask.stdout.on('data', (d) => process.stdout.write(`[flask] ${d}`));
flask.stderr.on('data', (d) => process.stderr.write(`[flask] ${d}`));
flask.on('exit', (code) => process.stderr.write(`[flask] exited with code ${code}\n`));

// Give Flask time to boot
await sleep(2000);

// Start Vite dev server (proxies all routes to Flask per vite.config.ts)
const vite = spawn('npx', ['vite', '--port', VITE_PORT, '--strictPort'], {
  stdio: 'inherit',
  env: process.env,
});

vite.on('exit', (code) => {
  try { flask.kill(); } catch {}
  process.exit(code ?? 0);
});

process.on('SIGINT', () => {
  try { vite.kill(); } catch {}
  try { flask.kill(); } catch {}
  process.exit(0);
});

process.on('SIGTERM', () => {
  try { vite.kill(); } catch {}
  try { flask.kill(); } catch {}
  process.exit(0);
});
