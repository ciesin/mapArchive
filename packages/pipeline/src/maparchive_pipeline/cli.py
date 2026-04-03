"""CLI entry point for the CIESIN Map Archive pipeline."""

import click

from .manifest import load_manifest
from .stac_builder import build_catalog
from .config import DEFAULT_OUTPUT_DIR


@click.group()
def main():
    """CIESIN Map Archive pipeline — process maps into a STAC catalog."""
    pass


@main.command()
@click.option(
    "--manifest", "-m",
    required=True,
    type=click.Path(exists=True),
    help="Path to the manifest CSV file.",
)
@click.option(
    "--output", "-o",
    default=str(DEFAULT_OUTPUT_DIR),
    type=click.Path(),
    help="Output directory for STAC catalog JSON.",
)
def build(manifest: str, output: str):
    """Build a STAC catalog from a manifest CSV."""
    click.echo(f"Loading manifest: {manifest}")
    rows = load_manifest(manifest)
    click.echo(f"  {len(rows)} items loaded")

    click.echo(f"Building STAC catalog -> {output}")
    catalog = build_catalog(rows, output)
    click.echo(f"  Catalog '{catalog.id}' written with {len(list(catalog.get_children()))} collections")


@main.command()
@click.option("--manifest", "-m", required=True, type=click.Path(exists=True))
@click.option("--local-dir", "-d", required=True, type=click.Path(exists=True))
@click.option("--rclone", "use_rclone", is_flag=True, default=False,
              help="Use rclone for bulk upload instead of boto3.")
@click.option("--rclone-remote", default=None,
              help="rclone remote name (overrides RCLONE_REMOTE in .env).")
@click.option("--transfers", default=32, show_default=True,
              help="Number of parallel transfers (rclone only).")
@click.option("--dry-run", is_flag=True,
              help="Show what would be uploaded without transferring (rclone only).")
@click.option("--r2-prefix", default="maps", show_default=True,
              help="Key prefix (subdirectory) within the R2 bucket.")
def upload(manifest: str, local_dir: str, use_rclone: bool, rclone_remote, transfers, dry_run, r2_prefix):
    """Upload map files to Cloudflare R2.

    By default uses boto3 (per-file, good for small/incremental uploads).
    Pass --rclone for bulk uploads — parallel transfers, automatic skip of
    already-uploaded files.
    """
    if use_rclone:
        from .rclone_upload import rclone_copy
        rclone_copy(
            local_dir,
            remote_name=rclone_remote,
            transfers=transfers,
            dry_run=dry_run,
            r2_prefix=r2_prefix,
        )
    else:
        from .r2_upload import upload_manifest_files
        rows = load_manifest(manifest)
        click.echo(f"Uploading {len(rows)} files to R2...")
        keys = upload_manifest_files(rows, local_dir)
        click.echo(f"  {len(keys)} files uploaded")


@main.command("setup-rclone")
@click.option("--remote-name", default=None,
              help="rclone remote name to create (overrides RCLONE_REMOTE in .env).")
@click.option("--overwrite", is_flag=True,
              help="Replace existing remote if it already exists.")
def setup_rclone(remote_name, overwrite):
    """Bootstrap an rclone R2 remote from .env credentials.

    Reads R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME
    from your .env and writes a named remote to ~/.config/rclone/rclone.conf.
    Safe to re-run.
    """
    from .rclone_upload import setup_remote
    setup_remote(remote_name=remote_name, overwrite=overwrite)


@main.command()
@click.option("--manifest", "-m", required=True, type=click.Path(exists=True))
@click.option("--dest-dir", "-d", required=True, type=click.Path())
def download(manifest: str, dest_dir: str):
    """Download map files from Google Drive."""
    from .drive import download_manifest_files

    rows = load_manifest(manifest)
    click.echo(f"Downloading {len(rows)} files from Google Drive...")
    downloaded = download_manifest_files(rows, dest_dir)
    click.echo(f"  {len(downloaded)} files downloaded")


@main.command()
@click.option(
    "--catalog-dir", "-c",
    default=str(DEFAULT_OUTPUT_DIR),
    type=click.Path(exists=True),
)
def ingest(catalog_dir: str):
    """Ingest a STAC catalog into Cloudflare D1."""
    from .d1_ingest import ingest_catalog

    click.echo(f"Ingesting catalog from {catalog_dir} into D1...")
    cols, items = ingest_catalog(catalog_dir)
    click.echo(f"  {cols} collections, {items} items ingested")


@main.command()
@click.option("--manifest", "-m", required=True, type=click.Path(exists=True))
@click.option("--output", "-o", default=str(DEFAULT_OUTPUT_DIR), type=click.Path())
@click.option("--local-dir", "-d", required=True, type=click.Path(exists=True))
def sync(manifest: str, output: str, local_dir: str):
    """Run the full pipeline: build catalog, upload to R2, ingest to D1."""
    from .r2_upload import upload_manifest_files
    from .d1_ingest import ingest_catalog

    rows = load_manifest(manifest)
    click.echo(f"[1/3] Building STAC catalog ({len(rows)} items)...")
    build_catalog(rows, output)

    click.echo("[2/3] Uploading files to R2...")
    upload_manifest_files(rows, local_dir)

    click.echo("[3/3] Ingesting catalog into D1...")
    cols, items = ingest_catalog(output)
    click.echo(f"Done: {cols} collections, {items} items synced")


@main.command()
@click.option("--folder-id", required=True, help="Google Drive folder ID to scan.")
@click.option(
    "--creds",
    default="scripts/misc/analytics/scripts/drive_credentials.json",
    type=click.Path(),
    help="Path to OAuth client credentials JSON.",
)
@click.option("--output", "-o", default=None, type=click.Path(), help="Output CSV path.")
@click.option("--shared-drive-id", default=None, help="Shared drive ID (if applicable).")
@click.option("--filter-text", default=None, help="Only include files whose name contains this text.")
@click.option("--filter-admin0", default=None, help="Only include files matching this admin0 code.")
@click.option("--filter-usecase", default=None, help="Only include files matching this useCase.")
@click.option("--no-normalize", is_flag=True, help="Keep original admin0 codes (skip ISO normalization).")
@click.option("--dry-run", is_flag=True, help="Scan and print stats without writing CSV.")
def generate(folder_id, creds, output, shared_drive_id, filter_text, filter_admin0, filter_usecase, no_normalize, dry_run):
    """Generate a manifest CSV by scanning a Google Drive folder."""
    from .generate_manifest import run_generate

    run_generate(
        folder_id=folder_id,
        creds_file=creds,
        output=output,
        shared_drive_id=shared_drive_id,
        filter_text=filter_text,
        filter_admin0=filter_admin0,
        filter_usecase=filter_usecase,
        no_normalize=no_normalize,
        dry_run=dry_run,
    )
