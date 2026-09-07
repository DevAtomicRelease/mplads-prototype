import tailwindcss from '@tailwindcss/postcss';
import react from '@vitejs/plugin-react';
import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';

// Local data stays in a separate loopback service, outside the static build.
export default defineConfig({
  css: { postcss: { plugins: [tailwindcss()] } },
  resolve: { alias: { '@': fileURLToPath(new URL('.', import.meta.url)) } },
  server: {
    host: '127.0.0.1',
    port: 3000,
    proxy: { '/api': 'http://127.0.0.1:8765' },
  },
  build: { outDir: 'dist/local' },
  plugins: [react()],
});
