/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",         // build to static HTML/CSS/JS in out/
  trailingSlash: true,      // out/index.html, out/404.html etc.
};

module.exports = nextConfig;

