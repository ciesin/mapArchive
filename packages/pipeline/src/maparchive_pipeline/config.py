"""Configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Anchor all relative paths to packages/pipeline/, not cwd
PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent

load_dotenv(PIPELINE_ROOT / ".env")


# Google Drive (OAuth client credentials — not a service account key)
_creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "drive_credentials.json")
GOOGLE_CREDENTIALS_PATH = (
    Path(_creds_path) if Path(_creds_path).is_absolute()
    else PIPELINE_ROOT / _creds_path
)
GOOGLE_TOKEN_CACHE = PIPELINE_ROOT / "token.pickle"

# Cloudflare R2 (S3-compatible)
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "")
R2_ENDPOINT = (
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else ""
)
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

# Cloudflare D1 (REST API)
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", R2_ACCOUNT_ID)
D1_DATABASE_ID = os.getenv("D1_DATABASE_ID", "")

# rclone
RCLONE_REMOTE = os.getenv("RCLONE_REMOTE", "")

# Pipeline defaults
DEFAULT_OUTPUT_DIR = PIPELINE_ROOT / "output"
STAC_VERSION = "1.1.0"
