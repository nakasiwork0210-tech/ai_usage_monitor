import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// GitHub Pages: https://nakasiwork0210-tech.github.io/ai_usage_monitor/
export default defineConfig({
  base: "/ai_usage_monitor/",
  plugins: [react(), tailwindcss()],
  build: {
    outDir: "../docs",
    emptyOutDir: true,
  },
});
