import type { STACCatalog, STACCollection, STACItem, STACLink } from './stac';

const STAC_BASE =
  (import.meta.env.PUBLIC_STAC_BASE_URL as string | undefined) ??
  'https://dev.ciesin.app/stac/static-maps';

async function stacFetch<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`STAC fetch failed: ${url} (${res.status})`);
  return res.json() as Promise<T>;
}

export function stacBase(): string {
  return STAC_BASE;
}

export function collectionUrl(slugPath: string): string {
  return `${STAC_BASE}/${slugPath}/collection.json`;
}

export function resolveHref(href: string, base: string): string {
  return new URL(href, base).toString();
}

/** Extract the relative slug segment from a child collection href like ./lubumbashi/collection.json */
export function extractChildSlug(href: string): string {
  return href.replace(/^\.\//, '').replace(/\/collection\.json$/, '');
}

/**
 * Humanize a slug segment for breadcrumb/display:
 * - 2-3 lowercase letters (country codes) → uppercase (e.g. "cod" → "COD")
 * - Otherwise → title-case words (e.g. "public-health" → "Public Health")
 */
export function slugToLabel(slug: string): string {
  if (/^[a-z]{2,3}$/.test(slug)) return slug.toUpperCase();
  return slug
    .split('-')
    .map((s) => s.charAt(0).toUpperCase() + s.slice(1))
    .join(' ');
}

export async function fetchCatalog(): Promise<STACCatalog> {
  return stacFetch<STACCatalog>(`${STAC_BASE}/catalog.json`);
}

export async function fetchCollection(slugPath: string): Promise<STACCollection> {
  return stacFetch<STACCollection>(collectionUrl(slugPath));
}

export async function fetchItem(itemUrl: string): Promise<STACItem> {
  return stacFetch<STACItem>(itemUrl);
}

/** Fetch a set of items concurrently, resolving each link href relative to baseUrl */
export async function fetchItemsByLinks(
  links: STACLink[],
  baseUrl: string,
): Promise<STACItem[]> {
  if (links.length === 0) return [];
  return Promise.all(links.map((l) => fetchItem(resolveHref(l.href, baseUrl))));
}
