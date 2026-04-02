import type { APIRoute } from 'astro';
import { MOCK_COLLECTIONS } from '../../lib/mock-data';

export const prerender = false;

export const GET: APIRoute = async () => {
  // TODO: Replace with D1 query via db.ts once bindings are provisioned
  // const db = context.locals.runtime.env.DB;
  // const collections = await getCollections(db);

  return new Response(JSON.stringify(MOCK_COLLECTIONS), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
