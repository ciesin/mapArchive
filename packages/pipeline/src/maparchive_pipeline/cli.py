"""CLI entry point for the CIESIN Map Archive pipeline."""

import click

from pathlib import Path

from .manifest import load_manifest, save_manifest
from .stac_builder import build_catalog
from .config import DEFAULT_OUTPUT_DIR, PIPELINE_ROOT


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
    default=str(DEFAULT_OUTPUT_DIR / "stac"),
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
@click.option("--with-overviews", is_flag=True,
              help="Also upload overview WebPs co-located in --local-dir (boto3 only).")
@click.option("--with-thumbnails", is_flag=True,
              help="Also upload thumbnail WebPs co-located in --local-dir (boto3 only).")
def upload(manifest: str, local_dir: str, use_rclone: bool, rclone_remote, transfers, dry_run, r2_prefix, with_overviews, with_thumbnails):
    """Upload map files to Cloudflare R2.

    By default uses boto3 (per-file, good for small/incremental uploads).
    Pass --rclone for bulk uploads — parallel transfers, automatic skip of
    already-uploaded files.

    Pass --with-overviews and/or --with-thumbnails to also upload the pre-generated
    WebP assets produced by `archive overviews` (they live alongside the originals in
    --local-dir).  These uploads always use boto3 regardless of --rclone.
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

    if with_overviews or with_thumbnails:
        rows = load_manifest(manifest)

    if with_overviews:
        from .r2_upload import upload_overview_files
        click.echo(f"Uploading overview images from {local_dir}...")
        keys = upload_overview_files(rows, local_dir)

    if with_thumbnails:
        from .r2_upload import upload_thumbnail_files
        click.echo(f"Uploading thumbnail images from {local_dir}...")
        keys = upload_thumbnail_files(rows, local_dir)


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
@click.option("--workers", default=16, show_default=True,
              help="Parallel download workers.")
@click.option("--chunk-size-mb", default=8, show_default=True,
              help="Download chunk size in MB.")
@click.option("--retries", default=5, show_default=True,
              help="Retries per chunk on transient errors.")
@click.option("--verify-checksum", is_flag=True,
              help="Verify Drive md5Checksum after download.")
def download(
    manifest: str,
    dest_dir: str,
    workers: int,
    chunk_size_mb: int,
    retries: int,
    verify_checksum: bool,
):
    """Download map files from Google Drive."""
    from .drive import download_manifest_files

    rows = load_manifest(manifest)
    click.echo(f"Downloading {len(rows)} files from Google Drive...")
    downloaded = download_manifest_files(
        rows,
        dest_dir,
        workers=workers,
        chunksize=chunk_size_mb * 1024 * 1024,
        num_retries=retries,
        verify_checksum=verify_checksum,
    )
    click.echo(f"  {len(downloaded)} files downloaded")


@main.command()
@click.option(
    "--catalog-dir", "-c",
    default=str(DEFAULT_OUTPUT_DIR / "stac"),
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
@click.option(
    "--manifest", "-m",
    required=True,
    type=click.Path(exists=True),
    help="Manifest CSV to enrich (output of `archive generate`).",
)
@click.option(
    "--spatial-dir", "-s",
    default=str(PIPELINE_ROOT / "input" / "spatial"),
    type=click.Path(exists=True),
    show_default=True,
    help="Directory containing GRID3 boundary CSVs.",
)
@click.option(
    "--output", "-o",
    default=None,
    type=click.Path(),
    help="Output CSV path (default: <manifest_stem>_enriched.csv beside input).",
)
@click.option("--dry-run", is_flag=True, help="Report match stats without writing output.")
def enrich(manifest: str, spatial_dir: str, output, dry_run: bool):
    """Enrich a manifest CSV with GRID3 spatial boundary metadata.

    Joins each row's admin_tree to the nearest pagename_* boundary, adding
    canonical pagenames, grid3id, and a fine-grained spatial bbox.
    Run after `archive generate` and before `archive build`.
    """
    from .enrich_manifest import run_enrich

    run_enrich(
        manifest_path=manifest,
        spatial_dir=spatial_dir,
        output_path=output,
        dry_run=dry_run,
    )


@main.command()
@click.option("--manifest", "-m", required=True, type=click.Path(exists=True),
              help="Manifest CSV (output of `archive enrich` or `archive generate`).")
@click.option("--input-dir", "-i", required=True, type=click.Path(exists=True),
              help="Local directory containing downloaded map files.")
@click.option("--no-thumbnails", is_flag=True,
              help="Skip thumbnail generation.")
@click.option("--max-px", default=4000, show_default=True,
              help="Maximum dimension (px) of the output overview WebP.")
@click.option("--workers", default=0, show_default=True,
              help="Parallel worker threads (0 = os.cpu_count()).")
@click.option("--output", "-o", default=None, type=click.Path(),
              help="Output manifest CSV path (default: <manifest_stem>_overviews.csv).")
@click.option("--manifest-only", "manifest_only", is_flag=True,
              help="Record existing overview/thumbnail keys without generating new images.")
def overviews(manifest: str, input_dir: str, no_thumbnails: bool, max_px: int, workers: int, output, manifest_only: bool):
    """Generate overview and thumbnail WebP images for map images.

    Overviews and thumbnails are written alongside the originals in --input-dir,
    keeping all assets for each map co-located.

    Overviews (max --max-px on longest side) are only generated for images whose
    area exceeds 100 MP or whose longest side exceeds 50,000 px.  Thumbnails
    (400 px wide, height preserves ISO 216 aspect ratio) are generated for every
    image; when an overview exists it is used as the thumbnail source.

    Writes an updated manifest CSV with width_px, height_px, overview_key, and
    thumbnail_key populated.  Pass that manifest to `archive build` and
    `archive upload` to publish the assets.

    Pass --manifest-only to skip image generation entirely: dimensions are still
    measured and any already-generated sibling files are recorded in the manifest.

    This command is idempotent — already-generated files are skipped.
    """
    from .overview_generator import generate_overviews

    rows = load_manifest(manifest)
    if manifest_only:
        click.echo(f"Scanning {len(rows)} images for existing assets (manifest-only)...")
    else:
        click.echo(f"Processing {len(rows)} images (input: {input_dir}, workers: {workers or 'cpu_count'})...")

    enriched = generate_overviews(
        rows,
        input_dir=Path(input_dir),
        generate_thumbnails=not no_thumbnails,
        max_px=max_px,
        workers=workers,
        manifest_only=manifest_only,
    )

    if output is None:
        p = Path(manifest)
        output = str(p.parent / f"{p.stem}_overviews.csv")

    save_manifest(enriched, output)
    n_overviews = sum(1 for r in enriched if r.overview_key)
    n_thumbnails = sum(1 for r in enriched if r.thumbnail_key)
    n_dims = sum(1 for r in enriched if r.width_px is not None)
    click.echo(f"  {n_dims} images measured, {n_overviews} overviews, {n_thumbnails} thumbnails{'found' if manifest_only else 'generated'}")
    click.echo(f"  Manifest saved: {output}")


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
