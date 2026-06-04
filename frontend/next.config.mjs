/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // /api/backend/* is handled by app/api/backend/[...path]/route.ts
  // (Route Handler bypasses the ~30s rewrite proxy timeout, needed for long LLM responses)
};

export default nextConfig;
