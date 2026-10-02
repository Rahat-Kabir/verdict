import { defineConfig } from "astro/config";

// Static frontend; the local dev proxy keeps browser requests on the same origin.
export default defineConfig({
  site: "https://verdict.local",
  trailingSlash: "ignore",
  vite: { server: { proxy: { "/api": "http://127.0.0.1:8000" } } },
});
