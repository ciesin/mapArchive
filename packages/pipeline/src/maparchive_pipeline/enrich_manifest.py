"""
Enrich a pipeline manifest CSV with spatial boundary metadata.

Joins manifest rows to GRID3 boundary CSVs via admin_tree → pagename_* lookup
(case-insensitive).  On match, overwrites bbox_west/south/east/north with the
finer-grained spatial boundary and adds spatial_level + grid3id.

Pipeline position: after `archive generate`, before `archive build`.
"""

import csv
import glob
import os
from pathlib import Path

# Ordered from most to least granular so the deepest match wins when multiple
# pagename_* columns appear in a single file.
_PAGENAME_LEVELS = ["pagename_airesante", "pagename_zonesante", "pagename_antenne", "pagename_province"]
_LEVEL_NAME = {
    "pagename_airesante": "airesante",
    "pagename_zonesante": "zonesante",
    "pagename_antenne": "antenne",
    "pagename_province": "province",
}
_ALL_PAGENAMES = set(_PAGENAME_LEVELS)

ENRICH_FIELDS = [
    "spatial_level",
    "grid3id",
]

_EMPTY_ENRICH = {f: "" for f in ENRICH_FIELDS}


def _strip_bom(s: str) -> str:
    return s.lstrip("\ufeff")


def load_spatial_index(spatial_dir: str | Path) -> dict:
    """
    Scan *spatial_dir* recursively for CSV files that contain a pagename_*
    key column.  Returns a dict mapping lowercase pagename → enrichment record.

    Each record contains:
      spatial_level, pagename_province, pagename_antenne, pagename_zonesante,
      pagename_airesante, grid3id, xmin/south/east/north
    """
    index: dict[str, dict] = {}
    pattern = str(Path(spatial_dir) / "**" / "*.csv")
    for path in glob.glob(pattern, recursive=True):
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                continue
            # Normalise header: strip BOM from first field name
            fieldnames = [_strip_bom(c) for c in reader.fieldnames]
            reader.fieldnames = fieldnames

            # Detect key column — pick deepest pagename level present
            key_col = next(
                (lvl for lvl in _PAGENAME_LEVELS if lvl in fieldnames),
                None,
            )
            if key_col is None:
                continue

            for row in reader:
                key = _strip_bom(row.get(key_col, "")).strip().lower()
                if not key:
                    continue

                record: dict[str, str] = {
                    "spatial_level": _LEVEL_NAME[key_col],
                    "pagename_province": row.get("pagename_province", "").strip(),
                    "pagename_antenne": row.get("pagename_antenne", "").strip(),
                    "pagename_zonesante": row.get("pagename_zonesante", "").strip(),
                    "pagename_airesante": row.get("pagename_airesante", "").strip(),
                    "grid3id": row.get("grid3id", "").strip(),
                    "xmin": row.get("xmin", "").strip(),
                    "ymin": row.get("ymin", "").strip(),
                    "xmax": row.get("xmax", "").strip(),
                    "ymax": row.get("ymax", "").strip(),
                }
                # Fill the matching level's own pagename from the key column
                # (in case the CSV doesn't carry a self-referential column).
                if not record[key_col]:
                    record[key_col] = row.get(key_col, "").strip()

                # Deeper match wins if the same key appears in multiple files.
                existing = index.get(key)
                if existing is None or (
                    _PAGENAME_LEVELS.index(key_col)
                    < _PAGENAME_LEVELS.index(
                        next(k for k, v in _LEVEL_NAME.items() if v == existing["spatial_level"])
                    )
                ):
                    index[key] = record

    return index


def enrich_rows(rows: list[dict], index: dict) -> tuple[list[dict], dict]:
    """
    Return enriched rows and a stats dict:
      matched, unmatched

    On a successful match the row's bbox_west/south/east/north are overwritten
    with the finer-grained spatial boundary from the index (xmin/ymin/xmax/ymax).
    pagename_* fields from the index are not written to output.
    """
    stats = {"matched": 0, "unmatched": 0}
    enriched = []
    for row in rows:
        key = row.get("admin_tree", "").strip().lower()
        record = index.get(key)
        if record:
            merged = {**row, **{f: record[f] for f in ENRICH_FIELDS}}
            merged["bbox_west"] = record["xmin"]
            merged["bbox_south"] = record["ymin"]
            merged["bbox_east"] = record["xmax"]
            merged["bbox_north"] = record["ymax"]
            enriched.append(merged)
            stats["matched"] += 1
        else:
            enriched.append({**row, **_EMPTY_ENRICH})
            stats["unmatched"] += 1
    return enriched, stats


def run_enrich(
    manifest_path: str | Path,
    spatial_dir: str | Path,
    output_path: str | Path | None = None,
    dry_run: bool = False,
) -> Path:
    """
    Enrich *manifest_path* with spatial metadata from *spatial_dir*.
    Writes the result to *output_path* (defaults to
    ``<manifest_stem>_enriched.csv`` beside the input file).
    Returns the output path.
    """
    manifest_path = Path(manifest_path)
    spatial_dir = Path(spatial_dir)

    if output_path is None:
        output_path = manifest_path.with_stem(manifest_path.stem + "_enriched")
    output_path = Path(output_path)

    print(f"Loading spatial index from {spatial_dir} ...")
    index = load_spatial_index(spatial_dir)
    print(f"  {len(index)} spatial boundaries indexed")

    print(f"Loading manifest: {manifest_path} ...")
    with open(manifest_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        base_fields = list(reader.fieldnames or [])
    print(f"  {len(rows)} rows loaded")

    enriched, stats = enrich_rows(rows, index)

    print(f"\n  Matched:   {stats['matched']}")
    print(f"  Unmatched: {stats['unmatched']}")

    if dry_run:
        print("\n  Dry run — no CSV written.")
        return output_path

    output_path.parent.mkdir(parents=True, exist_ok=True)
    all_fields = base_fields + [f for f in ENRICH_FIELDS if f not in base_fields]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(enriched)

    print(f"\n  Written -> {output_path}")
    return output_path
