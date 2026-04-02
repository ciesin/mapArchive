"""Tests for manifest parsing and STAC catalog building."""

import tempfile
from pathlib import Path

from maparchive_pipeline.manifest import ManifestRow, load_manifest
from maparchive_pipeline.stac_builder import build_catalog


EXAMPLE_MANIFEST = Path(__file__).parent.parent / "manifests" / "example_manifest.csv"


def test_load_manifest():
    rows = load_manifest(EXAMPLE_MANIFEST)
    assert len(rows) == 4
    assert all(isinstance(r, ManifestRow) for r in rows)


def test_manifest_row_properties():
    rows = load_manifest(EXAMPLE_MANIFEST)
    row = rows[0]
    assert row.admin0 == "USA"
    assert row.keyword_list == ["precipitation", "rainfall", "northeast", "annual"]
    assert row.bbox == [-80.5, 37.0, -66.9, 47.5]
    assert "climate" in row.item_id
    assert row.r2_key == "maps/climate/USA/Northeast/precip-2024.jpg"


def test_build_catalog():
    rows = load_manifest(EXAMPLE_MANIFEST)
    with tempfile.TemporaryDirectory() as tmpdir:
        catalog = build_catalog(rows, tmpdir)
        assert catalog.id == "ciesin-map-archive"
        collections = list(catalog.get_children())
        assert len(collections) == 2
        theme_ids = sorted(c.id for c in collections)
        assert theme_ids == ["climate", "population"]

        # Check items exist
        all_items = list(catalog.get_items(recursive=True))
        assert len(all_items) == 4

        # Verify catalog was written to disk
        catalog_json = Path(tmpdir) / "catalog.json"
        assert catalog_json.exists()
