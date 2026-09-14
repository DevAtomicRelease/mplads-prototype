import { defineConfig, mergeConfig } from 'vite';
// eslint-disable-next-line -- vite loads this config; extension-less import keeps tsc happy
import base from './vite.config';

// Separate build/entrypoint keeps the previous three-source application intact.
export default mergeConfig(base, defineConfig({
  server: { port: 3001, proxy: { '/api': 'http://127.0.0.1:8766' } },
  build: { outDir: 'dist/six', rollupOptions: { input: 'six.html' } },
}));
