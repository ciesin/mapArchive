import type { APIRoute } from 'astro';
import { fetchCatalog, fetchCollection, extractChildSlug } from '../../lib/stac-client';

export const prerender = false;

export const GET: APIRoute = async () => {
  try {
    const catalog = await fetchCatalog();
    const childLinks = catalog.links.filter((l) => l.rel === 'child');
    const collections = (
      await Promise.all(
        childLinks.map(async (link) => {
          try {
            return await fetchCollection(extractChildSlug(link.href));
          } catch {
            return null;
          }
        }),
      )
    ).filter(Boolean);
    return new Response(JSON.stringify(collections), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  } catch {
    return new Response(JSON.stringify({ error: 'Failed to fetch catalog' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
};
