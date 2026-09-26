import tailwindcss from '@tailwindcss/postcss';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';

const API = 'http://127.0.0.1:8766';
// The six-source app is the only default entry (index.html); the archived three-source
// app lives at legacy.html and is never the default. The loopback backend enforces a
// same-origin / loopback / CSRF policy, so in development we make the proxied /api request
// look same-origin to it: changeOrigin rewrites the Host header to the backend, and we set
// Origin to match. This keeps every backend check intact for both reads and review writes,
// with no CORS relaxation and no disabled verification.
export default defineConfig({
  css: { postcss: { plugins: [tailwindcss()] } },
  resolve: { alias: { '@': fileURLToPath(new URL('.', import.meta.url)) } },
  server: {
    host: '127.0.0.1',
    port: 3000,
    strictPort: true,
    proxy: { '/api': { target: API, changeOrigin: true, headers: { Origin: API } } },
  },
  build: { outDir: 'dist' },
  plugins: [react()],
});
