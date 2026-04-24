/**
 * Patches dist/server/wrangler.json after `astro build`.
 *
 * The @astrojs/cloudflare adapter generates bindings (ASSETS, SESSION KV,
 * triggers) that are invalid in a Cloudflare Pages deployment:
 *   - ASSETS is reserved by Pages (injected automatically)
 *   - SESSION kv_namespace lacks a required string `id`
 *   - triggers must be omitted or a proper cron object, not {}
 */

import fs from 'fs';
import path from 'path';

const wranglerPath = path.resolve('dist/server/wrangler.json');

if (!fs.existsSync(wranglerPath)) {
  console.error('fix-wrangler: dist/server/wrangler.json not found — skipping');
  process.exit(0);
}

const config = JSON.parse(fs.readFileSync(wranglerPath, 'utf8'));

delete config.assets;         // ASSETS is reserved in Pages
delete config.kv_namespaces;  // SESSION binding has no id — not used
delete config.triggers;       // empty object is invalid shape

fs.writeFileSync(wranglerPath, JSON.stringify(config, null, 2));
console.log('fix-wrangler: patched dist/server/wrangler.json');
