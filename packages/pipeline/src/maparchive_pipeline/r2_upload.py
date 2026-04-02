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

    Expects local files at: local_dir/{theme}/{admin0}/{area}/{filename}
    Uploads to R2 at: maps/{theme}/{admin0}/{area}/{filename}

    Returns list of uploaded R2 keys.
    """
    local_dir = Path(local_dir)
    client = get_r2_client()
    uploaded: list[str] = []

    for row in rows:
        local_path = local_dir / row.theme / row.admin0 / row.area / row.filename
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        key = upload_file(client, local_path, row.r2_key)
        uploaded.append(key)

    return uploaded
