export interface STACCatalog {
  type: 'Catalog';
  id: string;
  stac_version: string;
  title?: string;
  description: string;
  links: STACLink[];
}

export interface STACCollection {
  type: 'Collection';
  id: string;
  stac_version: string;
  title: string;
  description: string;
  license: string;
  extent: {
    spatial: { bbox: number[][] };
    temporal: { interval: (string | null)[][] };
  };
  links: STACLink[];
}

export interface STACItem {
  type: 'Feature';
  stac_version: string;
  id: string;
  collection: string;
  geometry: GeoJSONGeometry;
  bbox: number[];
  properties: STACItemProperties;
  links: STACLink[];
  assets: Record<string, STACAsset>;
}

export interface STACItemProperties {
  title: string;
  description?: string;
  datetime: string;
  admin0?: string;
  area?: string;
  theme?: string;
  [key: string]: unknown;
}

export interface STACAsset {
  href: string;
  type?: string;
  title?: string;
  roles?: string[];
}

export interface STACLink {
  rel: string;
  href: string;
  type?: string;
  title?: string;
}

export interface GeoJSONGeometry {
  type: string;
  coordinates: unknown;
}

export interface SearchParams {
  q?: string;
  theme?: string;
  admin0?: string;
  bbox?: string;
  datetime?: string;
  limit?: number;
  offset?: number;
}

export interface SearchResult {
  items: STACItem[];
  total: number;
  limit: number;
  offset: number;
}

/** Summary row returned from D1 queries (not full STAC JSON) */
export interface ItemSummary {
  id: string;
  collection_id: string;
  title: string;
  description: string | null;
  datetime: string | null;
  admin0: string | null;
  area: string | null;
  theme: string | null;
  asset_href: string | null;
  asset_type: string | null;
}
