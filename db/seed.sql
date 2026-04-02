-- Seed data for local development
-- 2 collections, 4 sample items

INSERT INTO collections (id, title, description, license, bbox_west, bbox_south, bbox_east, bbox_north, temporal_start, temporal_end, stac_json) VALUES
('climate', 'Climate Maps', 'Maps related to climate patterns, projections, and environmental change.', 'CC-BY-4.0', -180, -90, 180, 90, '2000-01-01T00:00:00Z', NULL, '{
  "type": "Collection",
  "id": "climate",
  "stac_version": "1.1.0",
  "title": "Climate Maps",
  "description": "Maps related to climate patterns, projections, and environmental change.",
  "license": "CC-BY-4.0",
  "extent": {
    "spatial": {"bbox": [[-180, -90, 180, 90]]},
    "temporal": {"interval": [["2000-01-01T00:00:00Z", null]]}
  },
  "links": []
}'),
('population', 'Population Maps', 'Maps depicting population density, distribution, and demographic patterns.', 'CC-BY-4.0', -180, -90, 180, 90, '2000-01-01T00:00:00Z', NULL, '{
  "type": "Collection",
  "id": "population",
  "stac_version": "1.1.0",
  "title": "Population Maps",
  "description": "Maps depicting population density, distribution, and demographic patterns.",
  "license": "CC-BY-4.0",
  "extent": {
    "spatial": {"bbox": [[-180, -90, 180, 90]]},
    "temporal": {"interval": [["2000-01-01T00:00:00Z", null]]}
  },
  "links": []
}');

INSERT INTO items (id, collection_id, title, description, datetime, bbox_west, bbox_south, bbox_east, bbox_north, geometry_json, admin0, area, theme, keywords, license, asset_href, asset_type, stac_json) VALUES
('climate-usa-northeast-precip-2024', 'climate', 'Northeast US Precipitation Patterns 2024', 'Annual precipitation patterns across the northeastern United States for 2024.', '2024-01-01T00:00:00Z', -80.5, 37.0, -66.9, 47.5, '{"type":"Polygon","coordinates":[[[-80.5,37.0],[-66.9,37.0],[-66.9,47.5],[-80.5,47.5],[-80.5,37.0]]]}', 'USA', 'Northeast', 'climate', '["precipitation","rainfall","northeast","annual"]', 'CC-BY-4.0', 'maps/climate/USA/northeast/precip-2024.jpg', 'image/jpeg', '{
  "type": "Feature",
  "stac_version": "1.1.0",
  "id": "climate-usa-northeast-precip-2024",
  "collection": "climate",
  "geometry": {"type":"Polygon","coordinates":[[[-80.5,37.0],[-66.9,37.0],[-66.9,47.5],[-80.5,47.5],[-80.5,37.0]]]},
  "bbox": [-80.5, 37.0, -66.9, 47.5],
  "properties": {
    "title": "Northeast US Precipitation Patterns 2024",
    "description": "Annual precipitation patterns across the northeastern United States for 2024.",
    "datetime": "2024-01-01T00:00:00Z",
    "admin0": "USA",
    "area": "Northeast",
    "theme": "climate"
  },
  "links": [],
  "assets": {
    "original": {
      "href": "maps/climate/USA/northeast/precip-2024.jpg",
      "type": "image/jpeg",
      "title": "Original map image",
      "roles": ["data"]
    }
  }
}'),
('climate-bgd-dhaka-flood-risk-2023', 'climate', 'Dhaka Flood Risk Assessment 2023', 'Flood risk zones and vulnerability assessment for Dhaka, Bangladesh.', '2023-06-01T00:00:00Z', 90.2, 23.6, 90.6, 23.9, '{"type":"Polygon","coordinates":[[[90.2,23.6],[90.6,23.6],[90.6,23.9],[90.2,23.9],[90.2,23.6]]]}', 'BGD', 'Dhaka', 'climate', '["flood","risk","dhaka","bangladesh","vulnerability"]', 'CC-BY-4.0', 'maps/climate/BGD/dhaka/flood-risk-2023.jpg', 'image/jpeg', '{
  "type": "Feature",
  "stac_version": "1.1.0",
  "id": "climate-bgd-dhaka-flood-risk-2023",
  "collection": "climate",
  "geometry": {"type":"Polygon","coordinates":[[[90.2,23.6],[90.6,23.6],[90.6,23.9],[90.2,23.9],[90.2,23.6]]]},
  "bbox": [90.2, 23.6, 90.6, 23.9],
  "properties": {
    "title": "Dhaka Flood Risk Assessment 2023",
    "description": "Flood risk zones and vulnerability assessment for Dhaka, Bangladesh.",
    "datetime": "2023-06-01T00:00:00Z",
    "admin0": "BGD",
    "area": "Dhaka",
    "theme": "climate"
  },
  "links": [],
  "assets": {
    "original": {
      "href": "maps/climate/BGD/dhaka/flood-risk-2023.jpg",
      "type": "image/jpeg",
      "title": "Original map image",
      "roles": ["data"]
    }
  }
}'),
('pop-ind-mumbai-density-2024', 'population', 'Mumbai Population Density 2024', 'High-resolution population density map for the Mumbai metropolitan area.', '2024-01-01T00:00:00Z', 72.7, 18.8, 73.1, 19.3, '{"type":"Polygon","coordinates":[[[72.7,18.8],[73.1,18.8],[73.1,19.3],[72.7,19.3],[72.7,18.8]]]}', 'IND', 'Mumbai', 'population', '["population","density","mumbai","india","urban"]', 'CC-BY-4.0', 'maps/population/IND/mumbai/density-2024.jpg', 'image/jpeg', '{
  "type": "Feature",
  "stac_version": "1.1.0",
  "id": "pop-ind-mumbai-density-2024",
  "collection": "population",
  "geometry": {"type":"Polygon","coordinates":[[[72.7,18.8],[73.1,18.8],[73.1,19.3],[72.7,19.3],[72.7,18.8]]]},
  "bbox": [72.7, 18.8, 73.1, 19.3],
  "properties": {
    "title": "Mumbai Population Density 2024",
    "description": "High-resolution population density map for the Mumbai metropolitan area.",
    "datetime": "2024-01-01T00:00:00Z",
    "admin0": "IND",
    "area": "Mumbai",
    "theme": "population"
  },
  "links": [],
  "assets": {
    "original": {
      "href": "maps/population/IND/mumbai/density-2024.jpg",
      "type": "image/jpeg",
      "title": "Original map image",
      "roles": ["data"]
    }
  }
}'),
('pop-nga-lagos-settlement-2023', 'population', 'Lagos Settlement Extent 2023', 'Urban settlement extent and growth patterns for Lagos, Nigeria.', '2023-01-01T00:00:00Z', 3.1, 6.3, 3.7, 6.7, '{"type":"Polygon","coordinates":[[[3.1,6.3],[3.7,6.3],[3.7,6.7],[3.1,6.7],[3.1,6.3]]]}', 'NGA', 'Lagos', 'population', '["settlement","urban","lagos","nigeria","growth"]', 'CC-BY-4.0', 'maps/population/NGA/lagos/settlement-2023.jpg', 'image/jpeg', '{
  "type": "Feature",
  "stac_version": "1.1.0",
  "id": "pop-nga-lagos-settlement-2023",
  "collection": "population",
  "geometry": {"type":"Polygon","coordinates":[[[3.1,6.3],[3.7,6.3],[3.7,6.7],[3.1,6.7],[3.1,6.3]]]},
  "bbox": [3.1, 6.3, 3.7, 6.7],
  "properties": {
    "title": "Lagos Settlement Extent 2023",
    "description": "Urban settlement extent and growth patterns for Lagos, Nigeria.",
    "datetime": "2023-01-01T00:00:00Z",
    "admin0": "NGA",
    "area": "Lagos",
    "theme": "population"
  },
  "links": [],
  "assets": {
    "original": {
      "href": "maps/population/NGA/lagos/settlement-2023.jpg",
      "type": "image/jpeg",
      "title": "Original map image",
      "roles": ["data"]
    }
  }
}');
