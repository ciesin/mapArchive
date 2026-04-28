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
