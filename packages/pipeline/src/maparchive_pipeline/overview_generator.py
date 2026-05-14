"""Generate overview and thumbnail JPEGs for map images.

Overviews are generated only for images that exceed Cloudflare Images input limits
(100 MP area or 50 000 px on any side).  Thumbnails are generated for every image
and are sourced from the overview when one exists (more efficient), otherwise from
the original.

Processing is parallelised with ThreadPoolExecutor — the heavy lifting is done by
ImageMagick subprocesses so threads are appropriate (no GIL contention).
"""

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .manifest import ManifestRow

# _CF_MAX_AREA = 100_000_000  # px^2
# _CF_MAX_DIM = 50_000         # px on any side

# force generation for all
_CF_MAX_AREA = 1  # px^2
_CF_MAX_DIM = 1         # px on any side


_THUMBNAIL_W = 600
_THUMBNAIL_H = 400


def generate_overviews(
    rows: list[ManifestRow],
    input_dir: Path,
    generate_thumbnails: bool = True,
    max_px: int = 4000,
    workers: int = 0,
    manifest_only: bool = False,
) -> list[ManifestRow]:
    """Read pixel dimensions for every image, generate downscaled JPEG overviews
    for oversized images, and (when generate_thumbnails is True) generate thumbnails
    for all images.

    When manifest_only=True, no images are written; existing overview/thumbnail
    siblings are detected and their keys recorded, but nothing is generated.

    Overviews and thumbnails are written alongside the originals in input_dir,
    mirroring the same theme/admin directory structure.

    Processing runs in parallel across `workers` threads (default: os.cpu_count()).
    Returns a new list of ManifestRows with width_px, height_px, overview_key,
    and thumbnail_key populated where applicable.  Already-generated files are
    skipped (idempotent).
    """
    input_dir = Path(input_dir)

    actual_workers = workers or os.cpu_count() or 1
    total = len(rows)

    with ThreadPoolExecutor(max_workers=actual_workers) as executor:
        futures = {
            executor.submit(_process_row, row, input_dir, generate_thumbnails, max_px, manifest_only): i
            for i, row in enumerate(rows)
        }
        results: dict[int, ManifestRow] = {}
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            result_row, logs = future.result()
            results[idx] = result_row
            completed += 1
            for line in logs:
                print(f"  [{completed}/{total}] {line}")
            if completed % 500 == 0 or completed == total:
                print(f"  ... {completed}/{total} processed")

    return [results[i] for i in range(total)]


# ---------------------------------------------------------------------------
# Per-row worker
# ---------------------------------------------------------------------------

def _process_row(
    row: ManifestRow,
    input_dir: Path,
    generate_thumbnails: bool,
    max_px: int,
    manifest_only: bool = False,
) -> tuple[ManifestRow, list[str]]:
    """Process one row; returns (updated_row, notable_log_lines)."""
    logs: list[str] = []

    local_path = _find_local_file(row, input_dir)
    if local_path is None:
        expected = input_dir / row.theme.lower()
        for admin in row.admin_path:
            expected = expected / admin.lower()
        logs.append(f"! not found: {expected / row.filename_normalized}")
        return row, logs

    try:
        w, h = _identify(local_path)
    except subprocess.CalledProcessError as exc:
        logs.append(f"! identify failed ({local_path.name}): {exc.stderr.strip()}")
        return row, logs

    updates: dict = {"width_px": w, "height_px": h}

    overview_path = _sibling_path(local_path, "_overview.jpg")
    thumb_path = _sibling_path(local_path, "_thumbnail.jpg")

    if manifest_only:
        if overview_path.exists():
            updates["overview_key"] = _sibling_r2_key(row, "_overview.jpg")
        if generate_thumbnails and thumb_path.exists():
            updates["thumbnail_key"] = _sibling_r2_key(row, "_thumbnail.jpg")
        return row.model_copy(update=updates), logs

    if _needs_overview(w, h):
        if overview_path.exists():
            logs.append(f"skip overview (exists): {overview_path.name}  [{w}x{h}]")
        else:
            try:
                _convert(local_path, overview_path, max_px)
                logs.append(f"overview: {w}x{h} -> {overview_path.name}")
            except subprocess.CalledProcessError as exc:
                logs.append(f"! convert failed ({local_path.name}): {exc.stderr.strip()}")
                return row.model_copy(update=updates), logs
        updates["overview_key"] = _sibling_r2_key(row, "_overview.jpg")

    if generate_thumbnails:
        thumb_source = overview_path if overview_path.exists() else local_path
        if not thumb_path.exists():
            try:
                _make_thumbnail(thumb_source, thumb_path)
            except subprocess.CalledProcessError as exc:
                logs.append(f"! thumbnail failed ({local_path.name}): {exc.stderr.strip()}")
                return row.model_copy(update=updates), logs
        updates["thumbnail_key"] = _sibling_r2_key(row, "_thumbnail.jpg")

    return row.model_copy(update=updates), logs


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_local_file(row: ManifestRow, input_dir: Path) -> Path | None:
    base = input_dir / row.theme.lower()
    for admin in row.admin_path:
        base = base / admin.lower()
    normalized = base / row.filename_normalized
    legacy = base / row.filename
    if normalized.exists():
        return normalized
    if legacy.exists():
        return legacy
    return None


def _identify(path: Path) -> tuple[int, int]:
    """Return (width, height) for the first frame/page using ImageMagick identify."""
    result = subprocess.run(
        ["identify", "-format", "%wx%h", f"{path}[0]"],
        capture_output=True,
        text=True,
        check=True,
    )
    raw = result.stdout.strip().splitlines()[0]
    w, h = raw.split("x")
    return int(w), int(h)


def _needs_overview(w: int, h: int) -> bool:
    return w * h > _CF_MAX_AREA or max(w, h) > _CF_MAX_DIM


def _convert(src: Path, dest: Path, max_px: int) -> None:
    """Resize src to max_px on its longest side and write a JPEG to dest."""
    subprocess.run(
        [
            "convert", f"{src}[0]",
            "-resize", f"{max_px}x{max_px}>",
            "-quality", "90",
            str(dest),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def _make_thumbnail(src: Path, dest: Path) -> None:
    """Downscale src to fit within _THUMBNAIL_W x _THUMBNAIL_H, write JPEG."""
    subprocess.run(
        [
            "convert", f"{src}[0]",
            "-resize", f"{_THUMBNAIL_W}x{_THUMBNAIL_H}>",
            "-quality", "85",
            str(dest),
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def _sibling_path(original: Path, suffix: str) -> Path:
    """Return a path in the same directory as original with stem + suffix."""
    return original.parent / f"{original.stem}{suffix}"


def _sibling_r2_key(row: ManifestRow, suffix: str) -> str:
    """R2 key for an asset that lives alongside the original map file."""
    stem = Path(row.filename_normalized).stem
    admin_subpath = "/".join(a.lower() for a in row.admin_path)
    return f"maps/{row.theme.lower()}/{admin_subpath}/{stem}{suffix}"
