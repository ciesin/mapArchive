"""Configuration loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# Google Drive
GOOGLE_CREDENTIALS_PATH = os.getenv(
    "GOOGLE_CREDENTIALS_PATH", "drive_credentials.json"
)

# Cloudflare R2 (S3-compatible)
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "maparchive-maps")
R2_ENDPOINT = (
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else ""
)
R2_PUBLIC_URL = os.getenv("R2_PUBLIC_URL", "")

# Cloudflare D1 (REST API)
CF_API_TOKEN = os.getenv("CF_API_TOKEN", "")
CF_ACCOUNT_ID = os.getenv("CF_ACCOUNT_ID", R2_ACCOUNT_ID)
D1_DATABASE_ID = os.getenv("D1_DATABASE_ID", "")

# Pipeline defaults
DEFAULT_OUTPUT_DIR = Path("output")
STAC_VERSION = "1.1.0"
