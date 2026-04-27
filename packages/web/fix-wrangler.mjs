/**
 * Post-build shim for Cloudflare Pages + @astrojs/cloudflare v13.
 *
 * Astro/cloudflare v13 no longer outputs _worker.js for Pages CI/CD.
 * It generates dist/server/ (Worker) + dist/client/ (static assets) and
 * expects `wrangler deploy`. Pages CI can't run that, so we:
 *
 *   1. Bundle dist/server/entry.mjs into dist/client/_worker.js via esbuild.
 *   2. Delete .wrangler/deploy/config.json (redirects Pages away from wrangler.toml).
 *
 * wrangler.toml must have pages_build_output_dir = "./dist/client" so Pages
 * serves static assets from dist/client/ and picks up _worker.js for SSR.
 */

import fs from 'fs';
import path from 'path';
import { build } from 'esbuild';

const entryPoint = path.resolve('dist/server/entry.mjs');
const outFile    = path.resolve('dist/client/_worker.js');
const deployConf = path.resolve('.wrangler/deploy/config.json');

if (!fs.existsSync(entryPoint)) {
  console.error('fix-wrangler: dist/server/entry.mjs not found — aborting');
  process.exit(1);
}

await build({
  entryPoints: [entryPoint],
  bundle: true,
  outfile: outFile,
  format: 'esm',
  platform: 'browser',
  target: 'es2022',
  conditions: ['workerd', 'worker', 'browser'],
  external: ['cloudflare:*', 'node:*', '__STATIC_CONTENT_MANIFEST'],
  logLevel: 'warning',
});

console.log('fix-wrangler: bundled _worker.js →', outFile);

if (fs.existsSync(deployConf)) {
  fs.rmSync(deployConf);
  console.log('fix-wrangler: removed .wrangler/deploy/config.json');
}
