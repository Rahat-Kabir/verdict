import { defineConfig } from "astro/config";

// Verdict leaderboard — fully static, no server components needed.
export default defineConfig({
  site: "https://verdict.local",
  trailingSlash: "ignore",
});
