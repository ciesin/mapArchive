import type { STACCollection, STACItem, ItemSummary } from './stac';

export const MOCK_COLLECTIONS: STACCollection[] = [
  {
    type: 'Collection',
    id: 'climate',
    stac_version: '1.1.0',
    title: 'Climate Maps',
    description: 'Maps related to climate patterns, projections, and environmental change.',
    license: 'CC-BY-4.0',
    extent: {
      spatial: { bbox: [[-180, -90, 180, 90]] },
      temporal: { interval: [['2000-01-01T00:00:00Z', null]] },
    },
    links: [],
  },
  {
    type: 'Collection',
    id: 'population',
    stac_version: '1.1.0',
    title: 'Population Maps',
    description: 'Maps depicting population density, distribution, and demographic patterns.',
    license: 'CC-BY-4.0',
    extent: {
      spatial: { bbox: [[-180, -90, 180, 90]] },
      temporal: { interval: [['2000-01-01T00:00:00Z', null]] },
    },
    links: [],
  },
];

export const MOCK_ITEMS: STACItem[] = [
  {
    type: 'Feature',
    stac_version: '1.1.0',
    id: 'climate-usa-northeast-precip-2024',
    collection: 'climate',
    geometry: {
      type: 'Polygon',
      coordinates: [[[-80.5, 37.0], [-66.9, 37.0], [-66.9, 47.5], [-80.5, 47.5], [-80.5, 37.0]]],
    },
    bbox: [-80.5, 37.0, -66.9, 47.5],
    properties: {
      title: 'Northeast US Precipitation Patterns 2024',
      description: 'Annual precipitation patterns across the northeastern United States for 2024.',
      datetime: '2024-01-01T00:00:00Z',
      admin0: 'USA',
      area: 'Northeast',
      theme: 'climate',
    },
    links: [],
    assets: {
      original: {
        href: 'maps/climate/USA/northeast/precip-2024.jpg',
        type: 'image/jpeg',
        title: 'Original map image',
        roles: ['data'],
      },
    },
  },
  {
    type: 'Feature',
    stac_version: '1.1.0',
    id: 'climate-bgd-dhaka-flood-risk-2023',
    collection: 'climate',
    geometry: {
      type: 'Polygon',
      coordinates: [[[90.2, 23.6], [90.6, 23.6], [90.6, 23.9], [90.2, 23.9], [90.2, 23.6]]],
    },
    bbox: [90.2, 23.6, 90.6, 23.9],
    properties: {
      title: 'Dhaka Flood Risk Assessment 2023',
      description: 'Flood risk zones and vulnerability assessment for Dhaka, Bangladesh.',
      datetime: '2023-06-01T00:00:00Z',
      admin0: 'BGD',
      area: 'Dhaka',
      theme: 'climate',
    },
    links: [],
    assets: {
      original: {
        href: 'maps/climate/BGD/dhaka/flood-risk-2023.jpg',
        type: 'image/jpeg',
        title: 'Original map image',
        roles: ['data'],
      },
    },
  },
  {
    type: 'Feature',
    stac_version: '1.1.0',
    id: 'pop-ind-mumbai-density-2024',
    collection: 'population',
    geometry: {
      type: 'Polygon',
      coordinates: [[[72.7, 18.8], [73.1, 18.8], [73.1, 19.3], [72.7, 19.3], [72.7, 18.8]]],
    },
    bbox: [72.7, 18.8, 73.1, 19.3],
    properties: {
      title: 'Mumbai Population Density 2024',
      description: 'High-resolution population density map for the Mumbai metropolitan area.',
      datetime: '2024-01-01T00:00:00Z',
      admin0: 'IND',
      area: 'Mumbai',
      theme: 'population',
    },
    links: [],
    assets: {
      original: {
        href: 'maps/population/IND/mumbai/density-2024.jpg',
        type: 'image/jpeg',
        title: 'Original map image',
        roles: ['data'],
      },
    },
  },
  {
    type: 'Feature',
    stac_version: '1.1.0',
    id: 'pop-nga-lagos-settlement-2023',
    collection: 'population',
    geometry: {
      type: 'Polygon',
      coordinates: [[[3.1, 6.3], [3.7, 6.3], [3.7, 6.7], [3.1, 6.7], [3.1, 6.3]]],
    },
    bbox: [3.1, 6.3, 3.7, 6.7],
    properties: {
      title: 'Lagos Settlement Extent 2023',
      description: 'Urban settlement extent and growth patterns for Lagos, Nigeria.',
      datetime: '2023-01-01T00:00:00Z',
      admin0: 'NGA',
      area: 'Lagos',
      theme: 'population',
    },
    links: [],
    assets: {
      original: {
        href: 'maps/population/NGA/lagos/settlement-2023.jpg',
        type: 'image/jpeg',
        title: 'Original map image',
        roles: ['data'],
      },
    },
  },
];

export const MOCK_ITEM_SUMMARIES: ItemSummary[] = MOCK_ITEMS.map((item) => ({
  id: item.id,
  collection_id: item.collection,
  title: item.properties.title,
  description: item.properties.description ?? null,
  datetime: item.properties.datetime ?? null,
  admin0: (item.properties.admin0 as string) ?? null,
  area: (item.properties.area as string) ?? null,
  theme: (item.properties.theme as string) ?? null,
  asset_href: item.assets.original?.href ?? null,
  asset_type: item.assets.original?.type ?? null,
}));

/** Get unique themes from mock data */
export function getThemes(): string[] {
  return [...new Set(MOCK_ITEMS.map((i) => i.properties.theme).filter(Boolean) as string[])];
}

/** Get unique admin0 codes from mock data */
export function getAdmin0Codes(): string[] {
  return [...new Set(MOCK_ITEMS.map((i) => i.properties.admin0).filter(Boolean) as string[])];
}
