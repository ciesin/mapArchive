-- CIESIN STAC Database — D1 schema
-- Apply: wrangler d1 execute ciesin-stac --file=db/schema.sql [--remote]

CREATE TABLE IF NOT EXISTS collections (
  id          TEXT PRIMARY KEY,
  title       TEXT NOT NULL,
  description TEXT,
  theme       TEXT,          -- ciesin:theme
  admin_path  TEXT,          -- JSON array e.g. '["cod","haut-katanga"]'
  stac_json   TEXT NOT NULL  -- full collection JSON
);

CREATE TABLE IF NOT EXISTS items (
  id            TEXT PRIMARY KEY,
  collection_id TEXT NOT NULL REFERENCES collections(id),
  title         TEXT NOT NULL,
  description   TEXT,
  datetime      TEXT,

  -- ciesin: namespace fields (denormalized for fast filtering)
  theme         TEXT,    -- ciesin:theme        e.g. "public-health"
  use_case      TEXT,    -- ciesin:use_case     e.g. "reference-minimal"
  admin_level   INTEGER, -- ciesin:admin_level  0=country, 1=province, …
  admin0        TEXT,    -- ciesin:admin0       ISO country code e.g. "COD"
  admin1        TEXT,    -- ciesin:admin1       e.g. "Haut-Katanga"
  admin2        TEXT,    -- ciesin:admin2
  spatial_level TEXT,    -- ciesin:spatial_level e.g. "province", "antenne"
  admin_path    TEXT,    -- JSON array from parent collection
  page_size     TEXT,    -- ciesin:page_size    e.g. "a0"
  page_num      TEXT,    -- ciesin:page_num     e.g. "1-1"

  -- Bounding box (split for range queries)
  bbox_west   REAL,
  bbox_south  REAL,
  bbox_east   REAL,
  bbox_north  REAL,

  -- Asset URLs (pre-extracted so detail pages don't need to parse stac_json)
  thumbnail_href TEXT,
  original_href  TEXT,

  stac_json TEXT NOT NULL  -- full item JSON
);

CREATE INDEX IF NOT EXISTS idx_items_collection  ON items(collection_id);
CREATE INDEX IF NOT EXISTS idx_items_theme        ON items(theme);
CREATE INDEX IF NOT EXISTS idx_items_admin0       ON items(admin0);
CREATE INDEX IF NOT EXISTS idx_items_admin_level  ON items(admin_level);
CREATE INDEX IF NOT EXISTS idx_items_datetime     ON items(datetime DESC);

-- Full-text search over title, description, and admin names
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
  id          UNINDEXED,
  title,
  description,
  admin1,
  admin2,
  spatial_level,
  content     = items,
  content_rowid = rowid
);

-- Keep FTS in sync
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
  INSERT INTO items_fts(rowid, id, title, description, admin1, admin2, spatial_level)
  VALUES (new.rowid, new.id, new.title, new.description,
          new.admin1, new.admin2, new.spatial_level);
END;

CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
  INSERT INTO items_fts(items_fts, rowid, id, title, description, admin1, admin2, spatial_level)
  VALUES ('delete', old.rowid, old.id, old.title, old.description,
          old.admin1, old.admin2, old.spatial_level);
END;

CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
  INSERT INTO items_fts(items_fts, rowid, id, title, description, admin1, admin2, spatial_level)
  VALUES ('delete', old.rowid, old.id, old.title, old.description,
          old.admin1, old.admin2, old.spatial_level);
  INSERT INTO items_fts(rowid, id, title, description, admin1, admin2, spatial_level)
  VALUES (new.rowid, new.id, new.title, new.description,
          new.admin1, new.admin2, new.spatial_level);
END;
