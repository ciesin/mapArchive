"""Google Drive API client for downloading map files."""

import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .config import GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_CACHE

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service(creds_file=None, token_cache=None):
    """Authenticate via OAuth and return a Google Drive API service instance.

    Caches the token so re-authentication is only needed when it expires.
    """
    creds_file = Path(creds_file) if creds_file else GOOGLE_CREDENTIALS_PATH
    token_cache = Path(token_cache) if token_cache else GOOGLE_TOKEN_CACHE

    creds = None
    if token_cache.exists():
        with open(token_cache, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_cache, "wb") as f:
            pickle.dump(creds, f)

    return build("drive", "v3", credentials=creds)


def download_file(service, file_id: str, dest_path: str | Path) -> Path:
    """Download a single file from Google Drive by its file ID."""
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

    Skips files that already exist at the destination path.
    Returns a mapping of drive_file_id -> local file path.
    """
    dest_dir = Path(dest_dir)
    service = get_drive_service()
    downloaded: dict[str, Path] = {}

    total = len(manifest_rows)
    skipped = 0
    failed: list[str] = []

    for i, row in enumerate(manifest_rows, 1):
        # Mirror the admin hierarchy: theme/admin0/admin1/.../filename
        dest_path = dest_dir / row.theme
        for admin in row.admin_path:
            dest_path = dest_path / admin
        dest_path = dest_path / row.filename

        if dest_path.exists():
            downloaded[row.drive_file_id] = dest_path
            skipped += 1
            continue

        print(f"  [{i}/{total}] {row.filename}", end="\r")

        try:
            downloaded[row.drive_file_id] = download_file(
                service, row.drive_file_id, dest_path
            )
        except Exception as e:
            print(f"\n  ! Failed: {row.filename} — {e}")
            failed.append(row.filename)

    print()  # clear the \r line
    print(f"  Downloaded: {len(downloaded) - skipped}  Skipped (existing): {skipped}  Failed: {len(failed)}")
    if failed:
        print(f"  Failed files: {', '.join(failed[:10])}" + (" ..." if len(failed) > 10 else ""))

    return downloaded
