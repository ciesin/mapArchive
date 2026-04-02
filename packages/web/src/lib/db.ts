import type { STACCollection, STACItem, SearchParams, SearchResult, ItemSummary } from './stac';

/**
 * D1 query helpers.
 *
 * These accept a D1Database binding and return typed results.
 * In the skeleton phase, pages use mock-data.ts instead.
 * Wire these up once D1 is provisioned.
 */

export async function getCollections(db: D1Database): Promise<STACCollection[]> {
  const { results } = await db.prepare('SELECT stac_json FROM collections ORDER BY id').all();
  return results.map((row: Record<string, unknown>) => JSON.parse(row.stac_json as string));
}

export async function getCollection(db: D1Database, id: string): Promise<STACCollection | null> {
  const row = await db.prepare('SELECT stac_json FROM collections WHERE id = ?').bind(id).first();
  if (!row) return null;
  return JSON.parse(row.stac_json as string);
}

export async function getItem(db: D1Database, id: string): Promise<STACItem | null> {
  const row = await db.prepare('SELECT stac_json FROM items WHERE id = ?').bind(id).first();
  if (!row) return null;
  return JSON.parse(row.stac_json as string);
}

export async function searchItems(db: D1Database, params: SearchParams): Promise<SearchResult> {
  const conditions: string[] = [];
  const bindings: unknown[] = [];

  if (params.q) {
    conditions.push('id IN (SELECT id FROM items_fts WHERE items_fts MATCH ?)');
    bindings.push(params.q);
  }
  if (params.theme) {
    conditions.push('theme = ?');
    bindings.push(params.theme);
  }
  if (params.admin0) {
    conditions.push('admin0 = ?');
    bindings.push(params.admin0);
  }
  if (params.bbox) {
    const [west, south, east, north] = params.bbox.split(',').map(Number);
    conditions.push('bbox_east >= ? AND bbox_west <= ? AND bbox_north >= ? AND bbox_south <= ?');
    bindings.push(west, east, south, north);
  }

  const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
  const limit = params.limit ?? 20;
  const offset = params.offset ?? 0;

  const countQuery = `SELECT COUNT(*) as total FROM items ${where}`;
  const countRow = await db.prepare(countQuery).bind(...bindings).first<{ total: number }>();
  const total = countRow?.total ?? 0;

  const dataQuery = `SELECT stac_json FROM items ${where} ORDER BY datetime DESC LIMIT ? OFFSET ?`;
  const { results } = await db.prepare(dataQuery).bind(...bindings, limit, offset).all();
  const items = results.map((row: Record<string, unknown>) => JSON.parse(row.stac_json as string));

  return { items, total, limit, offset };
}

export async function getItemsByCollection(
  db: D1Database,
  collectionId: string,
  admin0?: string,
): Promise<ItemSummary[]> {
  let query = 'SELECT id, collection_id, title, description, datetime, admin0, area, theme, asset_href, asset_type FROM items WHERE collection_id = ?';
  const bindings: unknown[] = [collectionId];
  if (admin0) {
    query += ' AND admin0 = ?';
    bindings.push(admin0);
  }
  query += ' ORDER BY datetime DESC';
  const { results } = await db.prepare(query).bind(...bindings).all<ItemSummary>();
  return results;
}
