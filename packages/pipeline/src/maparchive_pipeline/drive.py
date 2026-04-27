"""Google Drive API client for downloading map files."""

import hashlib
import pickle
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from .config import GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_CACHE

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
DEFAULT_NUM_RETRIES = 5
DEFAULT_WORKERS = 16
DEFAULT_FILE_RETRIES = 2
RETRYABLE_STATUS = {403, 429, 500, 502, 503, 504}
_THREAD_LOCAL = threading.local()


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

    return build("drive", "v3", credentials=creds, cache_discovery=False)


def get_thread_drive_service():
    """Thread-local Drive service to avoid cross-thread HTTP reuse."""
    service = getattr(_THREAD_LOCAL, "service", None)
    if service is None:
        service = get_drive_service()
        _THREAD_LOCAL.service = service
    return service


def compute_md5(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute MD5 checksum for a file."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk_size)
            if not buf:
                break
            hasher.update(buf)
    return hasher.hexdigest()


def get_file_md5(service, file_id: str) -> str | None:
    """Fetch Drive md5Checksum for a file, if available."""
    metadata = service.files().get(
        fileId=file_id,
        fields="md5Checksum",
        supportsAllDrives=True,
    ).execute()
    return metadata.get("md5Checksum")


def download_file(
    service,
    file_id: str,
    dest_path: str | Path,
    *,
    chunksize: int = DEFAULT_CHUNK_SIZE,
    num_retries: int = DEFAULT_NUM_RETRIES,
    expected_md5: str | None = None,
) -> Path:
    """Download a single file from Google Drive by its file ID."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    request = service.files().get_media(
        fileId=file_id,
        supportsAllDrives=True,
    )
    with open(dest_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request, chunksize=chunksize)
        done = False
        while not done:
            _, done = downloader.next_chunk(num_retries=num_retries)

    if expected_md5:
        actual_md5 = compute_md5(dest_path)
        if actual_md5 != expected_md5:
            raise ValueError(
                f"MD5 mismatch for {dest_path.name}: expected {expected_md5}, got {actual_md5}"
            )

    return dest_path


def build_dest_path(dest_dir: Path, row) -> Path:
    """Build the local path for a manifest row."""
    dest_path = dest_dir / row.theme
    for admin in row.admin_path:
        dest_path = dest_path / admin
    return dest_path / row.filename


def is_retryable_error(error: Exception) -> bool:
    if isinstance(error, HttpError):
        status = getattr(error.resp, "status", None)
        return status in RETRYABLE_STATUS
    return False


def download_manifest_files(
    manifest_rows: list,
    dest_dir: str | Path,
    *,
    workers: int = DEFAULT_WORKERS,
    chunksize: int = DEFAULT_CHUNK_SIZE,
    num_retries: int = DEFAULT_NUM_RETRIES,
    verify_checksum: bool = False,
    progress_every: int = 25,
) -> dict[str, Path]:
    """Download all files referenced in manifest rows.

    Skips files that already exist at the destination path.
    Returns a mapping of drive_file_id -> local file path.
    """
    dest_dir = Path(dest_dir)
    downloaded: dict[str, Path] = {}

    skipped = 0
    failed: list[str] = []

    pending: list[tuple] = []
    for row in manifest_rows:
        dest_path = build_dest_path(dest_dir, row)
        if dest_path.exists():
            downloaded[row.drive_file_id] = dest_path
            skipped += 1
            continue
        pending.append((row, dest_path))

    def download_one(row, dest_path: Path):
        service = get_thread_drive_service()
        expected_md5 = None
        if verify_checksum:
            expected_md5 = get_file_md5(service, row.drive_file_id)
        attempts = 0
        while True:
            try:
                return download_file(
                    service,
                    row.drive_file_id,
                    dest_path,
                    chunksize=chunksize,
                    num_retries=num_retries,
                    expected_md5=expected_md5,
                )
            except Exception as e:
                attempts += 1
                if attempts > DEFAULT_FILE_RETRIES or not is_retryable_error(e):
                    raise
                time.sleep(min(60, 2 ** attempts))

    if workers <= 1:
        for i, (row, dest_path) in enumerate(pending, 1):
            print(f"  [{i}/{len(pending)}] {row.filename}", end="\r")
            try:
                downloaded[row.drive_file_id] = download_one(row, dest_path)
            except Exception as e:
                print(f"\n  ! Failed: {row.filename} — {e}")
                failed.append(row.filename)
    else:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(download_one, row, dest_path): row
                for row, dest_path in pending
            }
            completed = 0
            for future in as_completed(future_map):
                row = future_map[future]
                completed += 1
                try:
                    downloaded[row.drive_file_id] = future.result()
                except Exception as e:
                    print(f"\n  ! Failed: {row.filename} — {e}")
                    failed.append(row.filename)

                if completed % progress_every == 0 or completed == len(pending):
                    print(
                        f"  [{completed}/{len(pending)}] downloaded",
                        end="\r",
                    )

    print()  # clear the \r line
    print(
        f"  Downloaded: {len(downloaded) - skipped}  Skipped (existing): {skipped}  Failed: {len(failed)}"
    )
    if failed:
        print(f"  Failed files: {', '.join(failed[:10])}" + (" ..." if len(failed) > 10 else ""))

    return downloaded
