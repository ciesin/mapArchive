import type { APIRoute } from 'astro';

export const prerender = false;

export const GET: APIRoute = async () => {
  return new Response(
    JSON.stringify({ error: 'Item lookup by ID requires D1 database (not yet provisioned). Use the STAC catalog directly.' }),
    { status: 501, headers: { 'Content-Type': 'application/json' } },
  );
};
