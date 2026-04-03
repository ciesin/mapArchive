"""Build STAC Catalogs, Collections, and Items from a validated manifest."""

from datetime import datetime
from pathlib import Path

import pystac

from .config import STAC_VERSION, R2_PUBLIC_URL
from .manifest import ManifestRow


def build_catalog(
    rows: list[ManifestRow],
    output_dir: str | Path,
    catalog_id: str = "ciesin-map-archive",
    catalog_title: str = "CIESIN Map Archive",
    catalog_description: str = "Searchable archive of high-resolution maps from CIESIN, Columbia University",
) -> pystac.Catalog:
    """Build a complete STAC catalog from manifest rows and write to disk."""
    output_dir = Path(output_dir)

    catalog = pystac.Catalog(
        id=catalog_id,
        title=catalog_title,
        description=catalog_description,
    )

    # Group rows by theme to create collections
    themes: dict[str, list[ManifestRow]] = {}
    for row in rows:
        themes.setdefault(row.theme, []).append(row)

    for theme, theme_rows in themes.items():
        collection = _build_collection(theme, theme_rows)
        for row in theme_rows:
            item = _build_item(row)
            collection.add_item(item)
        catalog.add_child(collection)

    catalog.normalize_hrefs(str(output_dir))
    catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

    return catalog


def _build_collection(theme: str, rows: list[ManifestRow]) -> pystac.Collection:
    """Create a STAC Collection for a theme."""
    # Compute aggregate extent from all rows
    bboxes = [r.bbox for r in rows]
    west = min(b[0] for b in bboxes)
    south = min(b[1] for b in bboxes)
    east = max(b[2] for b in bboxes)
    north = max(b[3] for b in bboxes)

    dates = []
    for r in rows:
        try:
            dates.append(datetime.fromisoformat(r.date))
        except ValueError:
            pass

    temporal_start = min(dates) if dates else None
    temporal_end = max(dates) if dates else None

    extent = pystac.Extent(
        spatial=pystac.SpatialExtent(bboxes=[[west, south, east, north]]),
        temporal=pystac.TemporalExtent(intervals=[[temporal_start, temporal_end]]),
    )

    return pystac.Collection(
        id=theme,
        title=f"{theme.replace('-', ' ').title()} Maps",
        description=f"Maps related to {theme.replace('-', ' ')}.",
        extent=extent,
        license=rows[0].license if rows else "proprietary",
    )


def _build_item(row: ManifestRow) -> pystac.Item:
    """Create a STAC Item from a manifest row."""
    bbox = row.bbox
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [bbox[0], bbox[1]],
                [bbox[2], bbox[1]],
                [bbox[2], bbox[3]],
                [bbox[0], bbox[3]],
                [bbox[0], bbox[1]],
            ]
        ],
    }

    try:
        dt = datetime.fromisoformat(row.date)
    except ValueError:
        dt = None

    # Build admin properties dict — only include non-empty levels
    admin_props = {
        f"admin{i}": val
        for i, val in enumerate([row.admin0, row.admin1, row.admin2, row.admin3, row.admin4])
        if val
    }

    item = pystac.Item(
        id=row.item_id,
        geometry=geometry,
        bbox=bbox,
        datetime=dt,
        properties={
            "title": row.title,
            "description": row.description,
            **admin_props,
            "page_size": row.page_size,
            "theme": row.theme,
            "keywords": row.keyword_list,
            "source_attribution": row.source_attribution,
        },
    )

    # Asset: original map image
    asset_href = row.r2_key
    if R2_PUBLIC_URL:
        asset_href = f"{R2_PUBLIC_URL}/{row.r2_key}"

    item.add_asset(
        "original",
        pystac.Asset(
            href=asset_href,
            media_type=_guess_media_type(row.filename),
            title="Original map image",
            roles=["data"],
        ),
    )

    return item


def _guess_media_type(filename: str) -> str:
    """Guess MIME type from file extension."""
    ext = Path(filename).suffix.lower()
    return {
        ".jpg": pystac.MediaType.JPEG,
        ".jpeg": pystac.MediaType.JPEG,
        ".png": pystac.MediaType.PNG,
        ".tif": pystac.MediaType.GEOTIFF,
        ".tiff": pystac.MediaType.GEOTIFF,
        ".pdf": "application/pdf",
    }.get(ext, "application/octet-stream")
