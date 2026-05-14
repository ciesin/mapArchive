"""Upload map files to Cloudflare R2 via S3-compatible API."""

from pathlib import Path

import boto3

from .config import (
    R2_ENDPOINT,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
)
from .manifest import ManifestRow


def get_r2_client():
    """Create a boto3 S3 client configured for Cloudflare R2."""
    return boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )


CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".pdf": "application/pdf",
}


def upload_file(
    client,
    local_path: str | Path,
    r2_key: str,
    content_type: str | None = None,
) -> str:
    """Upload a single file to R2. Returns the R2 key."""
    local_path = Path(local_path)
    if content_type is None:
        content_type = CONTENT_TYPES.get(
            local_path.suffix.lower(), "application/octet-stream"
        )

    client.upload_file(
        str(local_path),
        R2_BUCKET_NAME,
        r2_key,
        ExtraArgs={"ContentType": content_type},
    )
    return r2_key


def upload_manifest_files(
    rows: list[ManifestRow],
    local_dir: str | Path,
) -> list[str]:
    """Upload all files from a manifest to R2.

        Local files are located using the same directory structure that
        `download_manifest_files` creates:
            local_dir/{theme}/{admin0}/{admin1}/.../{filename_normalized}

    Each file is uploaded to the normalized R2 key (row.r2_key), which uses
    filename_normalized and the canonical lowercase path.

    Returns list of uploaded R2 keys.
    """
    local_dir = Path(local_dir)
    client = get_r2_client()
    uploaded: list[str] = []
    failed: list[str] = []

    total = len(rows)
    for i, row in enumerate(rows, 1):
        # Mirror the download path: theme/admin0/admin1/.../filename_normalized
        local_path = local_dir / row.theme.lower()
        for admin in row.admin_path:
            local_path = local_path / admin.lower()
        normalized_path = local_path / row.filename_normalized
        legacy_path = local_path / row.filename

        print(f"  [{i}/{total}] {row.filename_normalized}", end="\r")

        if normalized_path.exists():
            source_path = normalized_path
        elif legacy_path.exists():
            source_path = legacy_path
            print(f"\n  ! Using legacy filename: {legacy_path.name}")
        else:
            print(f"\n  ! Not found: {normalized_path}")
            failed.append(row.filename)
            continue

        key = upload_file(client, source_path, row.r2_key)
        uploaded.append(key)

    print()
    print(f"  Uploaded: {len(uploaded)}  Failed: {len(failed)}")
    if failed:
        print(f"  Failed: {', '.join(failed[:10])}" + (" ..." if len(failed) > 10 else ""))

    return uploaded


def _upload_sibling_files(
    rows: list[ManifestRow],
    local_dir: str | Path,
    key_attr: str,
    suffix: str,
    label: str,
) -> list[str]:
    """Upload sibling assets (overviews, thumbnails) that live alongside originals.

    Files are located at local_dir/{theme}/{admin_path...}/{stem}{suffix}.
    Only rows where key_attr is non-empty are processed.
    """
    local_dir = Path(local_dir)
    client = get_r2_client()
    uploaded: list[str] = []
    skipped: int = 0

    target_rows = [r for r in rows if getattr(r, key_attr)]
    total = len(target_rows)

    for i, row in enumerate(target_rows, 1):
        stem = Path(row.filename_normalized).stem
        local_path = local_dir / row.theme.lower()
        for admin in row.admin_path:
            local_path = local_path / admin.lower()
        local_path = local_path / f"{stem}{suffix}"

        r2_key = getattr(row, key_attr)
        print(f"  [{i}/{total}] {r2_key}", end="\r")

        if not local_path.exists():
            print(f"\n  ! not found: {local_path}")
            skipped += 1
            continue

        upload_file(client, local_path, r2_key, "image/jpeg")
        uploaded.append(r2_key)

    print()
    print(f"  {label}: {len(uploaded)} uploaded, {skipped} skipped")
    return uploaded


def upload_overview_files(rows: list[ManifestRow], local_dir: str | Path) -> list[str]:
    """Upload pre-generated overview JPEGs from local_dir (co-located with originals)."""
    return _upload_sibling_files(rows, local_dir, "overview_key", "_overview.jpg", "Overviews")


def upload_thumbnail_files(rows: list[ManifestRow], local_dir: str | Path) -> list[str]:
    """Upload pre-generated thumbnail JPEGs from local_dir (co-located with originals)."""
    return _upload_sibling_files(rows, local_dir, "thumbnail_key", "_thumbnail.jpg", "Thumbnails")
