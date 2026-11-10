import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: true,
    proxy: {
      '/analyze': 'http://localhost:10000',
      '/reference-audio': 'http://localhost:10000',
      '/health': 'http://localhost:10000',
      '/mantras': 'http://localhost:10000',
    },
  },
})

