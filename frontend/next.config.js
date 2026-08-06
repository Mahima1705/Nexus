const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Produces a minimal, self-contained .next/standalone build (only the files
  // actually needed at runtime, with a bundled node_modules) — see Dockerfile.
  output: "standalone",
  turbopack: {
    // Without this, Turbopack's root auto-detection picks up an unrelated
    // package-lock.json in the user's home directory and misidentifies the
    // workspace root.
    root: path.resolve(__dirname),
  },
};

module.exports = nextConfig;
