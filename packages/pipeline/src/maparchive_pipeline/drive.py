"""Google Drive API client for downloading map files."""

import io
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .config import GOOGLE_CREDENTIALS_PATH

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service():
    """Authenticate and return a Google Drive API service instance."""
    credentials = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials)


def download_file(
    service, file_id: str, dest_path: str | Path
) -> Path:
    """Download a file from Google Drive by its file ID."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    request = service.files().get_media(fileId=file_id)
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    return dest_path


def download_manifest_files(
    manifest_rows: list,
    dest_dir: str | Path,
) -> dict[str, Path]:
    """Download all files referenced in manifest rows.

    Returns a mapping of drive_file_id -> local file path.
    """
    dest_dir = Path(dest_dir)
    service = get_drive_service()
    downloaded: dict[str, Path] = {}

    for row in manifest_rows:
        dest_path = dest_dir / row.theme / row.admin0 / row.area / row.filename
        if dest_path.exists():
            downloaded[row.drive_file_id] = dest_path
            continue
        downloaded[row.drive_file_id] = download_file(
            service, row.drive_file_id, dest_path
        )

    return downloaded
