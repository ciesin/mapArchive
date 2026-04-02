"""Ingest STAC metadata into Cloudflare D1 via REST API."""

import json
from pathlib import Path

import pystac
import requests

from .config import CF_API_TOKEN, CF_ACCOUNT_ID, D1_DATABASE_ID


def _d1_query(sql: str, params: list | None = None) -> dict:
    """Execute a SQL query against D1 via the Cloudflare REST API."""
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/d1/database/{D1_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
    }
    body: dict = {"sql": sql}
    if params:
        body["params"] = params

    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def ingest_catalog(catalog_path: str | Path) -> tuple[int, int]:
    """Read a static STAC catalog and ingest collections + items into D1.

    Returns (collections_inserted, items_inserted).
    """
    catalog = pystac.Catalog.from_file(str(Path(catalog_path) / "catalog.json"))
    collections_inserted = 0
    items_inserted = 0

    for collection in catalog.get_children():
        if not isinstance(collection, pystac.Collection):
            continue
        _ingest_collection(collection)
        collections_inserted += 1

        for item in collection.get_items(recursive=True):
            _ingest_item(item, collection.id)
            items_inserted += 1

    return collections_inserted, items_inserted


def _ingest_collection(collection: pystac.Collection) -> None:
    """Insert or replace a collection in D1."""
    extent = collection.extent
    spatial = extent.spatial.bboxes[0] if extent.spatial.bboxes else [None] * 4
    temporal = extent.temporal.intervals[0] if extent.temporal.intervals else [None, None]

    stac_json = json.dumps(collection.to_dict())

    _d1_query(
        """INSERT OR REPLACE INTO collections
           (id, title, description, license, bbox_west, bbox_south, bbox_east, bbox_north,
            temporal_start, temporal_end, stac_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            collection.id,
            collection.title or collection.id,
            collection.description,
            collection.license or "proprietary",
            spatial[0],
            spatial[1],
            spatial[2],
            spatial[3],
            temporal[0].isoformat() if temporal[0] else None,
            temporal[1].isoformat() if temporal[1] else None,
            stac_json,
        ],
    )


def _ingest_item(item: pystac.Item, collection_id: str) -> None:
    """Insert or replace an item in D1."""
    props = item.properties
    bbox = item.bbox or [None] * 4
    geometry_json = json.dumps(item.geometry) if item.geometry else None
    keywords = json.dumps(props.get("keywords", []))
    asset = item.assets.get("original")
    asset_href = asset.href if asset else None
    asset_type = asset.media_type if asset else None
    stac_json = json.dumps(item.to_dict())

    _d1_query(
        """INSERT OR REPLACE INTO items
           (id, collection_id, title, description, datetime,
            bbox_west, bbox_south, bbox_east, bbox_north,
            geometry_json, admin0, area, theme, keywords, license,
            asset_href, asset_type, stac_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            item.id,
            collection_id,
            props.get("title", item.id),
            props.get("description"),
            item.datetime.isoformat() if item.datetime else None,
            bbox[0],
            bbox[1],
            bbox[2],
            bbox[3],
            geometry_json,
            props.get("admin0"),
            props.get("area"),
            props.get("theme"),
            keywords,
            props.get("license", "proprietary"),
            asset_href,
            asset_type,
            stac_json,
        ],
    )
