"""Build STAC Catalogs, Collections, and Items from a validated manifest."""

from datetime import datetime
from pathlib import Path

import pystac

from .config import R2_PUBLIC_URL, CF_IMAGES_ZONE
from .manifest import ManifestRow


def build_catalog(
    rows: list[ManifestRow],
    output_dir: str | Path,
    catalog_id: str = "ciesin-map-archive",
    catalog_title: str = "CIESIN Map Archive",
    catalog_description: str = "Searchable archive of high-resolution maps from CIESIN, Columbia University",
) -> pystac.Catalog:
    """Build a hierarchical STAC catalog and write to disk.

    Structure:
        ROOT (Catalog)
        └── {theme} (Collection)  — aggregate spatial/temporal extent
            └── {admin0} (Catalog)
                └── {admin1} (Catalog)
                    └── ... (Catalogs)
                        └── item.json (Item, collection link → theme Collection)
    """
    output_dir = Path(output_dir)

    catalog = pystac.Catalog(
        id=catalog_id,
        title=catalog_title,
        description=catalog_description,
    )

    # Group rows by theme
    themes: dict[str, list[ManifestRow]] = {}
    for row in rows:
        themes.setdefault(row.theme, []).append(row)

    for theme, theme_rows in themes.items():
        collection = _build_collection(theme, theme_rows)
        catalog.add_child(collection)

        # catalog_nodes caches already-created Catalog objects by path tuple
        # to avoid O(n²) child lookups while building the hierarchy.
        # Keys: (admin0,), (admin0, admin1), ..., (admin0, ..., admin4)
        catalog_nodes: dict[tuple[str, ...], pystac.Catalog] = {}

        for row in theme_rows:
            item = _build_item(row)
            leaf = _get_admin_leaf(collection, row.admin_path, catalog_nodes)
            leaf.add_item(item)

    catalog.normalize_hrefs(str(output_dir))
    catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

    return catalog


def _get_admin_leaf(
    collection: pystac.Collection,
    admin_path: list[str],
    catalog_nodes: dict[tuple[str, ...], pystac.Catalog],
) -> pystac.Catalog | pystac.Collection:
    """Navigate or create the chain of admin Catalog nodes within a Collection.

    Returns the deepest Catalog (or the Collection itself if admin_path is empty).
    """
    current: pystac.Catalog | pystac.Collection = collection
    key: tuple[str, ...] = ()

    for admin in admin_path:
        key = key + (admin,)
        if key not in catalog_nodes:
            cat = pystac.Catalog(
                id=admin,
                description=f"Maps in {admin}",
            )
            current.add_child(cat)
            catalog_nodes[key] = cat
        current = catalog_nodes[key]

    return current


def _build_collection(theme: str, rows: list[ManifestRow]) -> pystac.Collection:
    """Create a STAC Collection for a theme with aggregate spatial/temporal extent."""
    bboxes = [r.bbox for r in rows]
    west  = min(b[0] for b in bboxes)
    south = min(b[1] for b in bboxes)
    east  = max(b[2] for b in bboxes)
    north = max(b[3] for b in bboxes)

    dates = []
    for r in rows:
        try:
            dates.append(datetime.fromisoformat(r.date))
        except ValueError:
            pass

    extent = pystac.Extent(
        spatial=pystac.SpatialExtent(bboxes=[[west, south, east, north]]),
        temporal=pystac.TemporalExtent(
            intervals=[[min(dates) if dates else None, max(dates) if dates else None]]
        ),
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
        "coordinates": [[
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[2], bbox[3]],
            [bbox[0], bbox[3]],
            [bbox[0], bbox[1]],
        ]],
    }

    try:
        dt = datetime.fromisoformat(row.date)
    except ValueError:
        dt = None

    # Only include non-empty admin levels in properties
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
            "page_num": row.page_num,
            "theme": row.theme,
            "keywords": row.keyword_list,
            "source_attribution": row.source_attribution,
        },
    )

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

    if CF_IMAGES_ZONE and R2_PUBLIC_URL:
        item.add_asset(
            "thumbnail",
            pystac.Asset(
                href=_cf_thumbnail_url(asset_href),
                media_type="image/webp",
                title="Thumbnail (400×300, webp)",
                roles=["thumbnail"],
            ),
        )

    return item


def _cf_thumbnail_url(asset_href: str) -> str:
    """Build a Cloudflare Images transform URL for a 400×300 thumbnail.

    Pattern: {CF_IMAGES_ZONE}/cdn-cgi/image/<options>/<source-image-url>
    Matches the getThumbnailUrl() convention in packages/web/src/lib/images.ts.
    """
    options = "width=400,height=300,fit=cover,format=webp"
    return f"{CF_IMAGES_ZONE}/cdn-cgi/image/{options}/{asset_href}"


def _guess_media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".jpg":  pystac.MediaType.JPEG,
        ".jpeg": pystac.MediaType.JPEG,
        ".png":  pystac.MediaType.PNG,
        ".tif":  pystac.MediaType.GEOTIFF,
        ".tiff": pystac.MediaType.GEOTIFF,
        ".pdf":  "application/pdf",
    }.get(ext, "application/octet-stream")
