import type { APIRoute } from 'astro';
import { MOCK_ITEMS } from '../../../lib/mock-data';

export const prerender = false;

export const GET: APIRoute = async ({ params }) => {
  const { id } = params;

  // TODO: Replace with D1 query via db.ts once bindings are provisioned
  // const db = context.locals.runtime.env.DB;
  // const item = await getItem(db, id!);

  const item = MOCK_ITEMS.find((i) => i.id === id);

  if (!item) {
    return new Response(JSON.stringify({ error: 'Item not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  return new Response(JSON.stringify(item), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
};
