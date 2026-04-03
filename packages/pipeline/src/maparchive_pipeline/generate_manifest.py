"""
Generate mapArchive pipeline manifests from Google Drive folder scans.

Scans Google Drive folders, parses structured filenames, auto-generates
metadata attributes, and outputs CSV manifests for the maparchive pipeline.

Filename convention:
  {pageSize}_{useCase}_{admin0}_{admin1}_{admin2}_{admin3}_{admin4}_{pageNum}_{date}.{ext}
  Example: a2_comprehensive-dtp1_RDC_SANKURU_LODJA_KATAKO-KOMBE_KIETE_1_20250602.jpg
"""

import csv
import json
import sys
import time
from pathlib import Path

import pycountry

from .config import PIPELINE_ROOT
from .drive import get_drive_service


# ---------------------------------------------------------------------------
# Bundled reference data
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent / "data"

with open(_DATA_DIR / "admin0_bbox.json") as _f:
    ADMIN0_BBOX: dict[str, list[float]] = json.load(_f)


# ---------------------------------------------------------------------------
# Configuration — edit these to match your project
# ---------------------------------------------------------------------------

# Map filename useCase values to manifest theme values.
# Unmapped useCases fall through as-is (lowercased, hyphens stripped).
USECASE_TO_THEME = {
    "comprehensive-dtp1": "comprehensive",
    "comprehensive-dtp2": "comprehensive",
    "comprehensive": "comprehensive",
    "climate": "climate",
    "population": "population",
    "health": "health",
    "infrastructure": "infrastructure",
    "settlement": "population",
}

# Folder names containing these substrings (case-insensitive) are skipped.
DEFAULT_IGNORE_FOLDERS = ["old", "archive", "check", "draft", "backup", "test"]

# Default license and attribution for generated manifest rows.
DEFAULT_LICENSE = "CC-BY-4.0"
DEFAULT_ATTRIBUTION = "CIESIN Columbia University"

# Non-standard admin0 codes used in filenames → ISO 3166-1 alpha-3.
# pycountry handles most lookups; add project-specific overrides here.
ADMIN0_OVERRIDES = {
    "RDC": "COD",
}


# ---------------------------------------------------------------------------
# Filename parsing
# ---------------------------------------------------------------------------

def parse_filename(filename):
    """
    Parse structured filename into metadata components.

    Expected: {pageSize}_{useCase}_{admin0}_{admin1}_{admin2}_{admin3}_{admin4}_{pageNum}_{date}.{ext}
    Returns a dict with parsed fields, or None values if parsing fails.
    """
    try:
        name_without_ext = filename.rsplit(".", 1)[0]
        parts = name_without_ext.split("_")

        if len(parts) >= 9:
            return {
                "page_size": parts[0],
                "use_case": parts[1],
                "admin0": parts[2],
                "admin1": parts[3],
                "admin2": parts[4],
                "admin3": parts[5],
                "admin4": parts[6],
                "page_num": parts[7],
                "raw_date": parts[8],
                "parsed": True,
            }
    except Exception:
        pass

    return {
        "page_size": None,
        "use_case": None,
        "admin0": None,
        "admin1": None,
        "admin2": None,
        "admin3": None,
        "admin4": None,
        "page_num": None,
        "raw_date": None,
        "parsed": False,
    }


# ---------------------------------------------------------------------------
# ISO code + bbox resolution via pycountry + bundled data
# ---------------------------------------------------------------------------

def resolve_admin0(code, normalize=True):
    """
    Normalize an admin0 code to ISO 3166-1 alpha-3.

    Checks project overrides first, then pycountry (alpha-2 and alpha-3).
    Returns the original code uppercased if no match is found.
    """
    if not code:
        return ""
    code = code.upper()
    if not normalize:
        return code

    # Project-specific overrides
    if code in ADMIN0_OVERRIDES:
        return ADMIN0_OVERRIDES[code]

    # Already a valid alpha-3?
    match = pycountry.countries.get(alpha_3=code)
    if match:
        return match.alpha_3

    # Maybe an alpha-2?
    match = pycountry.countries.get(alpha_2=code)
    if match:
        return match.alpha_3

    return code


def get_country_name(alpha3):
    """Look up the English country name for an ISO alpha-3 code."""
    match = pycountry.countries.get(alpha_3=alpha3)
    return match.name if match else alpha3


def resolve_bbox(admin0):
    """Look up country-level bbox from bundled Natural Earth data."""
    return ADMIN0_BBOX.get(admin0, [None, None, None, None])


# ---------------------------------------------------------------------------
# Attribute generation
# ---------------------------------------------------------------------------

def _format_admin(value):
    """SANKURU → Sankuru, KATAKO-KOMBE → Katako-Kombe."""
    if not value:
        return ""
    return "-".join(w.capitalize() for w in value.split("-"))


def _format_date(raw_date):
    """20250602 → 2025-06-02."""
    if not raw_date or len(raw_date) != 8:
        return ""
    try:
        return f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    except (ValueError, IndexError):
        return ""


def resolve_theme(use_case):
    """Map a filename useCase to a manifest theme."""
    if not use_case:
        return "uncategorized"
    key = use_case.lower()
    if key in USECASE_TO_THEME:
        return USECASE_TO_THEME[key]
    return key.rstrip("0123456789").rstrip("-") or key


def build_manifest_row(drive_file, parsed, normalize_admin0=True):
    """Convert a Drive file + parsed filename into a manifest CSV row."""
    admin0 = resolve_admin0(parsed["admin0"], normalize=normalize_admin0)
    country_name = get_country_name(admin0)
    theme = resolve_theme(parsed["use_case"])
    date = _format_date(parsed["raw_date"])
    bbox = resolve_bbox(admin0)

    area = _format_admin(parsed["admin1"])

    # Build title: "Comprehensive Dtp1 — Kiete, Katako-Kombe, Lodja, Sankuru, DR Congo (2025)"
    admin_parts = [
        _format_admin(parsed[k])
        for k in ("admin4", "admin3", "admin2", "admin1")
        if parsed.get(k)
    ]
    location_str = ", ".join(admin_parts) if admin_parts else country_name
    year = date[:4] if date else ""
    use_label = (parsed["use_case"] or theme).replace("-", " ").title()
    title = f"{use_label} — {location_str}, {country_name}"
    if year:
        title += f" ({year})"

    # Build description
    desc_parts = [f"{use_label} map"]
    if location_str:
        desc_parts.append(f"covering {location_str}, {country_name}")
    if date:
        desc_parts.append(f"dated {date}")
    if parsed.get("page_num"):
        desc_parts.append(f"(page {parsed['page_num']})")
    description = " ".join(desc_parts) + "."

    # Keywords from admin levels, theme, and useCase
    kw = {theme}
    if parsed["use_case"]:
        kw.add(parsed["use_case"].lower().replace("-", " "))
    for level in ("admin0", "admin1", "admin2", "admin3", "admin4"):
        val = parsed.get(level)
        if val:
            kw.add(val.lower())
    keywords = ",".join(sorted(kw))

    return {
        "drive_file_id": drive_file["id"],
        "filename": drive_file["name"],
        "theme": theme,
        "admin0": admin0,
        "area": area,
        "title": title,
        "description": description,
        "date": date,
        "bbox_west": bbox[0] if bbox[0] is not None else "",
        "bbox_south": bbox[1] if bbox[1] is not None else "",
        "bbox_east": bbox[2] if bbox[2] is not None else "",
        "bbox_north": bbox[3] if bbox[3] is not None else "",
        "keywords": keywords,
        "license": DEFAULT_LICENSE,
        "source_attribution": DEFAULT_ATTRIBUTION,
    }


# ---------------------------------------------------------------------------
# Drive folder scanning
# ---------------------------------------------------------------------------

SUPPORTED_MIMES = {"application/pdf", "image/jpeg", "image/png", "image/tiff"}


def scan_folder(
    service,
    folder_id,
    *,
    shared_drive_id=None,
    ignore_folders=None,
    filter_text=None,
    filter_admin0=None,
    filter_usecase=None,
    normalize_admin0=True,
    folder_path="",
    progress=None,
):
    """Recursively scan a Drive folder, parse filenames, yield manifest rows."""
    if ignore_folders is None:
        ignore_folders = DEFAULT_IGNORE_FOLDERS
    if progress is None:
        progress = {"scanned": 0, "matched": 0, "skipped_parse": 0, "t": time.time()}

    page_token = None
    while True:
        params = {
            "q": f"'{folder_id}' in parents",
            "fields": "nextPageToken, files(id, mimeType, name, size)",
            "pageToken": page_token,
            "pageSize": 1000,
        }
        if shared_drive_id:
            params.update({
                "corpora": "drive",
                "driveId": shared_drive_id,
                "includeItemsFromAllDrives": True,
                "supportsAllDrives": True,
            })

        try:
            results = service.files().list(**params).execute()
        except Exception as e:
            print(f"\n  API error in {folder_path or 'root'}: {e}", file=sys.stderr)
            break

        for item in results.get("files", []):
            if item["mimeType"] == "application/vnd.google-apps.folder":
                name_lower = item["name"].lower()
                if any(kw in name_lower for kw in ignore_folders):
                    continue
                sub_path = f"{folder_path}/{item['name']}" if folder_path else item["name"]
                yield from scan_folder(
                    service,
                    item["id"],
                    shared_drive_id=shared_drive_id,
                    ignore_folders=ignore_folders,
                    filter_text=filter_text,
                    filter_admin0=filter_admin0,
                    filter_usecase=filter_usecase,
                    normalize_admin0=normalize_admin0,
                    folder_path=sub_path,
                    progress=progress,
                )
                continue

            if item["mimeType"] not in SUPPORTED_MIMES:
                continue

            progress["scanned"] += 1

            if filter_text and filter_text not in item["name"]:
                continue

            parsed = parse_filename(item["name"])
            if not parsed["parsed"]:
                progress["skipped_parse"] += 1
                continue

            raw_admin0 = resolve_admin0(parsed["admin0"], normalize=normalize_admin0)
            if filter_admin0 and raw_admin0 != filter_admin0.upper():
                continue
            if filter_usecase and parsed["use_case"] != filter_usecase:
                continue

            row = build_manifest_row(item, parsed, normalize_admin0=normalize_admin0)
            progress["matched"] += 1

            if progress["matched"] % 100 == 0 or (time.time() - progress["t"]) > 10:
                print(
                    f"  Progress: {progress['matched']} matched / "
                    f"{progress['scanned']} scanned ...",
                    end="\r",
                )
                progress["t"] = time.time()

            yield row

        page_token = results.get("nextPageToken")
        if not page_token:
            break


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------

MANIFEST_FIELDS = [
    "drive_file_id",
    "filename",
    "theme",
    "admin0",
    "area",
    "title",
    "description",
    "date",
    "bbox_west",
    "bbox_south",
    "bbox_east",
    "bbox_north",
    "keywords",
    "license",
    "source_attribution",
]


def write_manifest(rows, output_path):
    """Write manifest rows to CSV."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main entry point (called by CLI or standalone)
# ---------------------------------------------------------------------------

def run_generate(
    folder_id,
    creds_file,
    output=None,
    shared_drive_id=None,
    ignore_folders=None,
    filter_text=None,
    filter_admin0=None,
    filter_usecase=None,
    no_normalize=False,
    dry_run=False,
):
    """Scan a Google Drive folder and generate a pipeline manifest CSV."""
    from datetime import datetime

    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = str(PIPELINE_ROOT / "manifests" / f"manifest_{timestamp}.csv")

    print(f"Authenticating with {creds_file} ...")
    service = get_drive_service(creds_file=creds_file)

    print(f"Scanning folder {folder_id} ...")
    if filter_text:
        print(f"  Filter (text): {filter_text}")
    if filter_admin0:
        print(f"  Filter (admin0): {filter_admin0}")
    if filter_usecase:
        print(f"  Filter (useCase): {filter_usecase}")

    start = time.time()
    progress = {"scanned": 0, "matched": 0, "skipped_parse": 0, "t": start}
    rows = list(
        scan_folder(
            service,
            folder_id,
            shared_drive_id=shared_drive_id,
            ignore_folders=ignore_folders,
            filter_text=filter_text,
            filter_admin0=filter_admin0,
            filter_usecase=filter_usecase,
            normalize_admin0=not no_normalize,
            progress=progress,
        )
    )
    elapsed = time.time() - start

    print(f"\n{'=' * 60}")
    print(f"Scan complete in {elapsed:.1f}s")
    print(f"  Files scanned:  {progress['scanned']}")
    print(f"  Matched:        {progress['matched']}")
    print(f"  Skipped (unparseable filename): {progress['skipped_parse']}")

    if rows:
        themes = {}
        admin0s = {}
        for r in rows:
            themes[r["theme"]] = themes.get(r["theme"], 0) + 1
            admin0s[r["admin0"]] = admin0s.get(r["admin0"], 0) + 1

        print(f"\n  Themes:")
        for t, c in sorted(themes.items(), key=lambda x: -x[1]):
            print(f"    {t}: {c}")
        print(f"\n  Admin0 codes (top 10):")
        for a, c in sorted(admin0s.items(), key=lambda x: -x[1])[:10]:
            name = get_country_name(a)
            print(f"    {a} ({name}): {c}")

        missing_bbox = sum(1 for r in rows if r["bbox_west"] == "")
        if missing_bbox:
            missing_codes = sorted({
                r["admin0"] for r in rows if r["bbox_west"] == ""
            })
            print(f"\n  Warning: {missing_bbox} rows missing bbox")
            print(f"  Missing codes: {', '.join(missing_codes)}")
            print(f"  Add entries to data/admin0_bbox.json to fix.")

    if dry_run:
        print(f"\n  Dry run — no CSV written.")
    elif rows:
        write_manifest(rows, output)
        print(f"\n  Manifest written: {output} ({len(rows)} rows)")
    else:
        print(f"\n  No matching files found — no CSV written.")

    print(f"{'=' * 60}")
    return rows
