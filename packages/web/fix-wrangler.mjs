/**
 * Patches dist/server/wrangler.json after `astro build`.
 *
 * The @astrojs/cloudflare adapter generates a Worker-style wrangler.json that
 * Cloudflare Pages rejects. Strip all Pages-incompatible fields before deploy.
 *
 * Fields removed:
 *   assets            — ASSETS binding is reserved by Pages (auto-injected)
 *   kv_namespaces     — SESSION entry has no required `id` string
 *   triggers          — empty {} is invalid; Pages manages cron triggers separately
 *   main              — Worker entry point declaration not supported in Pages config
 *   pages_build_output_dir — conflicts with `main` when both present in same file
 *   rules             — module rules not supported in Pages config
 *   no_bundle         — not supported in Pages config
 */

import fs from 'fs';
import path from 'path';

const wranglerPath = path.resolve('dist/server/wrangler.json');

if (!fs.existsSync(wranglerPath)) {
  console.error('fix-wrangler: dist/server/wrangler.json not found — skipping');
  process.exit(0);
}

const config = JSON.parse(fs.readFileSync(wranglerPath, 'utf8'));

delete config.assets;
delete config.kv_namespaces;
delete config.triggers;
delete config.main;
delete config.pages_build_output_dir;
delete config.rules;
delete config.no_bundle;

fs.writeFileSync(wranglerPath, JSON.stringify(config, null, 2));
console.log('fix-wrangler: patched dist/server/wrangler.json');
