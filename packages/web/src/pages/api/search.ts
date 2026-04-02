import type { APIRoute } from 'astro';
import { MOCK_ITEMS } from '../../lib/mock-data';
import type { STACItem } from '../../lib/stac';

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const q = url.searchParams.get('q') ?? '';
  const theme = url.searchParams.get('theme') ?? '';
  const admin0 = url.searchParams.get('admin0') ?? '';
  const bbox = url.searchParams.get('bbox') ?? '';
  const limit = Math.min(parseInt(url.searchParams.get('limit') ?? '20', 10), 100);
  const offset = parseInt(url.searchParams.get('offset') ?? '0', 10);

  // TODO: Replace with D1 query via db.ts once bindings are provisioned
  // const db = context.locals.runtime.env.DB;
  // const result = await searchItems(db, { q, theme, admin0, bbox, limit, offset });

  let filtered: STACItem[] = [...MOCK_ITEMS];

  if (q) {
    const lower = q.toLowerCase();
    filtered = filtered.filter(
      (i) =>
        i.properties.title.toLowerCase().includes(lower) ||
        (i.properties.description ?? '').toLowerCase().includes(lower) ||
        ((i.properties.area as string) ?? '').toLowerCase().includes(lower),
    );
  }
  if (theme) {
    filtered = filtered.filter((i) => i.properties.theme === theme);
  }
  if (admin0) {
    filtered = filtered.filter((i) => i.properties.admin0 === admin0);
  }
  if (bbox) {
    const [west, south, east, north] = bbox.split(',').map(Number);
    filtered = filtered.filter((i) => {
      const [bw, bs, be, bn] = i.bbox;
      return be >= west && bw <= east && bn >= south && bs <= north;
    });
  }

  const total = filtered.length;
  const items = filtered.slice(offset, offset + limit);

  return new Response(JSON.stringify({ items, total, limit, offset }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
