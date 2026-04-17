-- mapArchive D1 Schema
-- STAC-compliant metadata storage with full-text search

CREATE TABLE IF NOT EXISTS collections (
    id TEXT PRIMARY KEY,                    -- e.g., "comprehensive", "microplanning"
    title TEXT NOT NULL,
    description TEXT,
    license TEXT DEFAULT 'proprietary',
    bbox_west REAL,
    bbox_south REAL,
    bbox_east REAL,
    bbox_north REAL,
    temporal_start TEXT,                    -- ISO 8601
    temporal_end TEXT,                      -- ISO 8601
    stac_json TEXT NOT NULL,               -- Full STAC Collection JSON
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,                    -- theme-admin_chain-filename_stem
    collection_id TEXT NOT NULL REFERENCES collections(id),
    title TEXT NOT NULL,
    description TEXT,
    datetime TEXT,                          -- ISO 8601
    bbox_west REAL,
    bbox_south REAL,
    bbox_east REAL,
    bbox_north REAL,
    geometry_json TEXT,                     -- GeoJSON geometry as text
    admin0 TEXT,                            -- ISO 3166-1 alpha-3 country code
    admin1 TEXT,                            -- Province / state
    admin2 TEXT,                            -- District / territory
    admin3 TEXT,                            -- Sub-district / zone de santé
    admin4 TEXT,                            -- Aire de santé / locality
    page_size TEXT,                         -- Original layout page size (e.g., "a2", "a0")
    page_num TEXT,                          -- Page number within a multi-page set
    theme TEXT,                             -- Theme name (denormalized for search)
    keywords TEXT,                          -- JSON array as text
    license TEXT DEFAULT 'proprietary',
    asset_href TEXT,                        -- R2 URL to original image
    asset_type TEXT DEFAULT 'image/jpeg',   -- MIME type
    stac_json TEXT NOT NULL,               -- Full STAC Item JSON
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Search indexes
CREATE INDEX IF NOT EXISTS idx_items_collection ON items(collection_id);
CREATE INDEX IF NOT EXISTS idx_items_admin0     ON items(admin0);
CREATE INDEX IF NOT EXISTS idx_items_admin1     ON items(admin1);
CREATE INDEX IF NOT EXISTS idx_items_admin2     ON items(admin2);
CREATE INDEX IF NOT EXISTS idx_items_theme      ON items(theme);
CREATE INDEX IF NOT EXISTS idx_items_datetime   ON items(datetime);

-- Full-text search (SQLite FTS5)
-- All admin levels are indexed so users can search by province, district, etc.
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    id,
    title,
    description,
    keywords,
    admin0,
    admin1,
    admin2,
    admin3,
    admin4,
    theme,
    content='items',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync with the items table
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, id, title, description, keywords,
                          admin0, admin1, admin2, admin3, admin4, theme)
    VALUES (new.rowid, new.id, new.title, new.description, new.keywords,
            new.admin0, new.admin1, new.admin2, new.admin3, new.admin4, new.theme);
END;

CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, id, title, description, keywords,
                          admin0, admin1, admin2, admin3, admin4, theme)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.keywords,
            old.admin0, old.admin1, old.admin2, old.admin3, old.admin4, old.theme);
END;

CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, id, title, description, keywords,
                          admin0, admin1, admin2, admin3, admin4, theme)
    VALUES ('delete', old.rowid, old.id, old.title, old.description, old.keywords,
            old.admin0, old.admin1, old.admin2, old.admin3, old.admin4, old.theme);
    INSERT INTO items_fts(rowid, id, title, description, keywords,
                          admin0, admin1, admin2, admin3, admin4, theme)
    VALUES (new.rowid, new.id, new.title, new.description, new.keywords,
            new.admin0, new.admin1, new.admin2, new.admin3, new.admin4, new.theme);
END;
