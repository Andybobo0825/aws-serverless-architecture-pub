import { defineConfig } from 'vite';

export default defineConfig({
  define: {
    'global': 'globalThis'
  },
  build: {
    rollupOptions: {
      input: {
        app: 'index.html',
        admin: 'admin.html'
      }
    }
  }
});
