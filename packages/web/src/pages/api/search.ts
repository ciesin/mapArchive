import type { APIRoute } from 'astro';

export const prerender = false;

export const GET: APIRoute = async () => {
  return new Response(
    JSON.stringify({ error: 'Search API requires D1 database (not yet provisioned)' }),
    { status: 501, headers: { 'Content-Type': 'application/json' } },
  );
};
