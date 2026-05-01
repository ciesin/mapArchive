"""Build STAC Catalogs, Collections, and Items from a validated manifest.

Hierarchy
---------
ROOT (Catalog)
└── {theme} (Collection)          ← aggregate extent for all maps in a theme
    └── {admin0} (Collection)     ← e.g. "cod"
        └── {admin0-admin1} (Collection)   ← e.g. "cod-tshopo"
            └── ... (Collections, one per AOI level)
                └── item.json     ← one Item per map file

Collection IDs follow STAC best-practice searchable-identifier rules:
  lowercase, only [a-z0-9-._~], built by joining the admin path with "-".

Item properties for non-standard fields are namespaced "ciesin:*" per
STAC extension best-practices.
"""

from datetime import datetime
from pathlib import Path

import pystac
from pystac import layout

from .config import R2_PUBLIC_URL, CF_IMAGES_ZONE
from .manifest import ManifestRow


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_catalog(
    rows: list[ManifestRow],
    output_dir: str | Path,
    catalog_id: str = "ciesin-map-archive",
    catalog_title: str = "CIESIN Map Archive",
    catalog_description: str = "Searchable archive of high-resolution maps from CIESIN, Columbia University",
) -> pystac.Catalog:
    """Build a hierarchical STAC catalog and write to disk."""
    output_dir = Path(output_dir)

    catalog = pystac.Catalog(
        id=catalog_id,
        title=catalog_title,
        description=catalog_description,
    )

    themes: dict[str, list[ManifestRow]] = {}
    for row in rows:
        themes.setdefault(row.theme, []).append(row)

    for theme, theme_rows in themes.items():
        theme_collection = _build_theme_collection(theme, theme_rows)
        catalog.add_child(theme_collection)
        _build_aoi_hierarchy(theme_collection, theme_rows)

    layout_strategy = _build_nested_layout_strategy(output_dir)
    catalog.normalize_hrefs(str(output_dir), strategy=layout_strategy)
    catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)

    return catalog


# ---------------------------------------------------------------------------
# AOI collection hierarchy
# ---------------------------------------------------------------------------

def _build_aoi_hierarchy(
    theme_collection: pystac.Collection,
    rows: list[ManifestRow],
) -> None:
    """Build AOI-based sub-collections inside *theme_collection* and add items.

    Each unique admin-path prefix (e.g. ("cod",), ("cod","tshopo"), …) becomes
    a pystac.Collection whose spatial/temporal extent covers all rows beneath it.
    Items land in their exact-level collection.
    """
    # 1. Collect rows for every ancestor prefix of each row's admin path
    prefix_rows: dict[tuple[str, ...], list[ManifestRow]] = {}
    for row in rows:
        path = tuple(a.lower() for a in row.admin_path)
        for depth in range(1, len(path) + 1):
            prefix_rows.setdefault(path[:depth], []).append(row)

    # 2. Create collections, parents before children (sort by depth)
    aoi_collections: dict[tuple[str, ...], pystac.Collection] = {}

    for prefix in sorted(prefix_rows, key=len):
        prows = prefix_rows[prefix]
        first_row = prows[0]

        # Human-readable display name = most-specific admin component
        display_name = first_row.admin_path[len(prefix) - 1]
        breadcrumb = " > ".join(first_row.admin_path[: len(prefix)])

        coll = pystac.Collection(
            id="-".join(prefix),
            title=display_name,
            description=f"Maps covering {breadcrumb}",
            extent=_compute_extent(prows),
            license=first_row.license,
            providers=_build_providers(first_row.source_attribution),
        )
        coll.extra_fields["ciesin:theme"] = first_row.theme.lower()
        coll.extra_fields["ciesin:admin_path"] = list(prefix)

        parent: pystac.STACObject = (
            theme_collection if len(prefix) == 1 else aoi_collections[prefix[:-1]]
        )
        parent.add_child(coll)
        aoi_collections[prefix] = coll

    # 3. Add items to their exact-level (leaf) collection
    for row in rows:
        path = tuple(a.lower() for a in row.admin_path)
        aoi_collections[path].add_item(_build_item(row))


# ---------------------------------------------------------------------------
# Collection builders
# ---------------------------------------------------------------------------

def _build_theme_collection(theme: str, rows: list[ManifestRow]) -> pystac.Collection:
    """Create the top-level theme Collection with aggregate extent."""
    collection = pystac.Collection(
        id=theme,
        title=f"{theme.replace('-', ' ').title()} Maps",
        description=f"Archive of {theme.replace('-', ' ')} maps.",
        extent=_compute_extent(rows),
        license=rows[0].license if rows else "proprietary",
        providers=_build_providers(rows[0].source_attribution if rows else ""),
    )
    collection.extra_fields["ciesin:theme"] = theme.lower()
    collection.extra_fields["ciesin:admin_path"] = []
    return collection


def _compute_extent(rows: list[ManifestRow]) -> pystac.Extent:
    """Compute aggregate spatial + temporal extent from a set of rows."""
    bboxes = [r.bbox for r in rows if r.bbox[0] is not None]
    if bboxes:
        west  = min(b[0] for b in bboxes)
        south = min(b[1] for b in bboxes)
        east  = max(b[2] for b in bboxes)
        north = max(b[3] for b in bboxes)
    else:
        west, south, east, north = -180.0, -90.0, 180.0, 90.0

    dates: list[datetime] = []
    for r in rows:
        try:
            dates.append(datetime.fromisoformat(r.date))
        except (ValueError, AttributeError):
            pass

    return pystac.Extent(
        spatial=pystac.SpatialExtent([[west, south, east, north]]),
        temporal=pystac.TemporalExtent(
            [[min(dates) if dates else None, max(dates) if dates else None]]
        ),
    )


def _build_providers(attribution: str) -> list[pystac.Provider]:
    if not attribution:
        return []
    return [
        pystac.Provider(
            name=attribution,
            roles=[pystac.ProviderRole.PRODUCER, pystac.ProviderRole.LICENSOR],
        )
    ]


# ---------------------------------------------------------------------------
# Item builder
# ---------------------------------------------------------------------------

def _build_item(row: ManifestRow) -> pystac.Item:
    """Create a STAC Item from a manifest row.

    Custom (non-standard) properties are namespaced under "ciesin:" per
    STAC best-practices for searchable identifiers and extension hygiene.
    Standard STAC common-metadata fields (title, description, keywords)
    are used without a prefix.
    """
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
    except (ValueError, AttributeError):
        dt = None

    # Only include non-empty admin levels; namespace all custom properties
    admin_props = {
        f"ciesin:admin{i}": val
        for i, val in enumerate([row.admin0, row.admin1, row.admin2, row.admin3, row.admin4])
        if val
    }

    spatial_props = {
        k: v for k, v in {
            "ciesin:spatial_level": row.spatial_level,
            "ciesin:grid3id": row.grid3id,
        }.items() if v
    }

    item = pystac.Item(
        id=row.item_id,
        geometry=geometry,
        bbox=bbox,
        datetime=dt,
        properties={
            # --- STAC common metadata (no prefix) ---
            "title": row.title,
            "description": row.description,
            "keywords": row.keyword_list,
            # --- CIESIN-specific properties ---
            "ciesin:theme": row.theme,
            "ciesin:use_case": row.use_case,
            "ciesin:admin_level": row.admin_level,
            "ciesin:page_size": row.page_size,
            "ciesin:page_num": row.page_num,
            "ciesin:filename_original": row.filename,
            "ciesin:filename_normalized": row.filename_normalized,
            **admin_props,
            **spatial_props,
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
            title="Original static map",
            roles=["data", "visual"],
        ),
    )

    if CF_IMAGES_ZONE and R2_PUBLIC_URL:
        item.add_asset(
            "thumbnail",
            pystac.Asset(
                href=_cf_image_url(asset_href, "w=600,h=400,fit=scale-down,g=auto,f=auto"),
                media_type="image/webp",
                title="Thumbnail",
                roles=["thumbnail"],
            ),
        )
        item.add_asset(
            "overview",
            pystac.Asset(
                href=_cf_image_url(asset_href, "w=1200,fit=scale-down,f=auto,q=85"),
                media_type="image/webp",
                title="Overview (1200px)",
                roles=["overview"],
            ),
        )

    return item


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cf_image_url(asset_href: str, options: str) -> str:
    """Build a Cloudflare Images transform URL.

    Pattern: {CF_IMAGES_ZONE}/cdn-cgi/image/<options>/<source-image-url>
    See: https://developers.cloudflare.com/images/transform-images/transform-via-url/
    """
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


def _build_nested_layout_strategy(output_dir: Path) -> layout.CustomLayoutStrategy:
    base_dir = Path(output_dir)

    def _catalog_href(cat: pystac.Catalog, _parent_dir: str, is_root: bool) -> str:
        if is_root:
            return str(base_dir / cat.DEFAULT_FILE_NAME)
        return str(base_dir / cat.id / cat.DEFAULT_FILE_NAME)

    def _collection_href(col: pystac.Collection, _parent_dir: str, _is_root: bool) -> str:
        theme = col.extra_fields.get("ciesin:theme", "unknown")
        admin_path = col.extra_fields.get("ciesin:admin_path", [])
        if admin_path:
            return str(base_dir / theme / Path(*admin_path) / col.DEFAULT_FILE_NAME)
        return str(base_dir / theme / col.DEFAULT_FILE_NAME)

    def _item_href(item: pystac.Item, _parent_dir: str) -> str:
        theme = item.properties.get("ciesin:theme", "unknown")
        admin_path = _item_admin_path(item)
        return str(
            base_dir / theme / Path(*admin_path) / item.id / f"{item.id}.json"
        )

    return layout.CustomLayoutStrategy(
        catalog_func=_catalog_href,
        collection_func=_collection_href,
        item_func=_item_href,
    )


def _item_admin_path(item: pystac.Item) -> list[str]:
    levels = [
        item.properties.get("ciesin:admin0"),
        item.properties.get("ciesin:admin1"),
        item.properties.get("ciesin:admin2"),
        item.properties.get("ciesin:admin3"),
        item.properties.get("ciesin:admin4"),
    ]
    return [lvl.lower() for lvl in levels if lvl]
