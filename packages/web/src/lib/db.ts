import type { STACCollection, STACItem, SearchParams, SearchResult } from './stac';

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

  const countRow = await db
    .prepare(`SELECT COUNT(*) as total FROM items ${where}`)
    .bind(...bindings)
    .first<{ total: number }>();
  const total = countRow?.total ?? 0;

  const { results } = await db
    .prepare(`SELECT stac_json FROM items ${where} ORDER BY datetime DESC LIMIT ? OFFSET ?`)
    .bind(...bindings, limit, offset)
    .all();
  const items = results.map((row: Record<string, unknown>) => JSON.parse(row.stac_json as string));

  return { items, total, limit, offset };
}

export async function getItemsByCollectionPath(
  db: D1Database,
  adminPath: string[],   // e.g. ['cod', 'haut-katanga']
  adminLevel?: number,
): Promise<STACItem[]> {
  const pathJson = JSON.stringify(adminPath);
  let query = 'SELECT stac_json FROM items WHERE admin_path = ?';
  const bindings: unknown[] = [pathJson];
  if (adminLevel !== undefined) {
    query += ' AND admin_level = ?';
    bindings.push(adminLevel);
  }
  query += ' ORDER BY datetime DESC';
  const { results } = await db.prepare(query).bind(...bindings).all();
  return results.map((row: Record<string, unknown>) => JSON.parse(row.stac_json as string));
}
