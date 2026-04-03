"""Bulk upload to Cloudflare R2 via rclone."""

import shutil
import subprocess
import sys
from pathlib import Path

from .config import (
    R2_ACCOUNT_ID,
    R2_ACCESS_KEY_ID,
    R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME,
    R2_ENDPOINT,
    RCLONE_REMOTE,
)


def _require_rclone():
    """Raise a clear error if rclone is not on PATH."""
    if not shutil.which("rclone"):
        print(
            "Error: rclone not found on PATH.\n"
            "Install it from https://rclone.org/install/ or via:\n"
            "  sudo apt install rclone   (Debian/Ubuntu)\n"
            "  brew install rclone       (macOS)\n"
            "  winget install Rclone.Rclone  (Windows)",
            file=sys.stderr,
        )
        sys.exit(1)


def setup_remote(remote_name=None, overwrite=False):
    """
    Bootstrap an rclone S3/Cloudflare R2 remote from .env credentials.

    Writes a named remote to the user's rclone config (~/.config/rclone/rclone.conf).
    Safe to re-run — uses --non-interactive and confirms before overwriting an
    existing remote unless overwrite=True.
    """
    _require_rclone()

    remote_name = remote_name or RCLONE_REMOTE

    if not R2_ACCOUNT_ID or not R2_ACCESS_KEY_ID or not R2_SECRET_ACCESS_KEY:
        print(
            "Error: R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, and R2_SECRET_ACCESS_KEY "
            "must be set in your .env before running setup-rclone.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Check if the remote already exists
    result = subprocess.run(
        ["rclone", "listremotes"],
        capture_output=True, text=True,
    )
    existing = [r.rstrip(":") for r in result.stdout.splitlines()]

    if remote_name in existing and not overwrite:
        print(
            f"Remote '{remote_name}' already exists in rclone config.\n"
            f"Run with --overwrite to replace it."
        )
        return remote_name

    cmd = [
        "rclone", "config", "create", remote_name, "s3",
        "provider=Cloudflare",
        f"access_key_id={R2_ACCESS_KEY_ID}",
        f"secret_access_key={R2_SECRET_ACCESS_KEY}",
        f"endpoint={R2_ENDPOINT}",
        "acl=private",
        "--non-interactive",
    ]

    verb = "Updating" if remote_name in existing else "Creating"
    print(f"{verb} rclone remote '{remote_name}' -> endpoint: {R2_ENDPOINT}")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: rclone config create failed:\n{result.stderr}", file=sys.stderr)
        sys.exit(result.returncode)

    print(f"Remote '{remote_name}' configured successfully.")
    print(f"Verify with: rclone lsd {remote_name}:{R2_BUCKET_NAME}")
    return remote_name


def rclone_copy(
    local_dir: str | Path,
    remote_name=None,
    bucket=None,
    r2_prefix="maps",
    transfers=32,
    dry_run=False,
):
    """
    Copy a local directory tree to R2 using rclone.

    Uses `rclone copy` (non-destructive — never deletes files already in R2).
    Files already present in R2 with matching size/checksum are skipped.

    Args:
        local_dir:    Local directory to upload from.
        remote_name:  rclone remote name (defaults to RCLONE_REMOTE from .env).
        bucket:       R2 bucket name (defaults to R2_BUCKET_NAME from .env).
        r2_prefix:    Key prefix within the bucket (default: "maps").
        transfers:    Number of parallel transfers (default: 32).
        dry_run:      Print what would be transferred without uploading.
    """
    _require_rclone()

    remote_name = remote_name or RCLONE_REMOTE
    bucket = bucket or R2_BUCKET_NAME
    local_dir = Path(local_dir)
    destination = f"{remote_name}:{bucket}/{r2_prefix}"

    cmd = [
        "rclone", "copy",
        str(local_dir),
        destination,
        "--transfers", str(transfers),
        "--progress",
        "--stats", "10s",
        "--stats-one-line",
    ]
    if dry_run:
        cmd.append("--dry-run")

    action = "Dry-run: would copy" if dry_run else "Copying"
    print(f"{action}: {local_dir} -> {destination}  (transfers={transfers})")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"Error: rclone copy exited with code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)
