/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // For the single-container HuggingFace Space build we export a static site
  // that FastAPI serves. Enabled only when NEXT_OUTPUT_EXPORT=1 so `next dev`
  // and split deployments are unaffected.
  ...(process.env.NEXT_OUTPUT_EXPORT === "1"
    ? { output: "export", images: { unoptimized: true } }
    : {}),
};

export default nextConfig;
