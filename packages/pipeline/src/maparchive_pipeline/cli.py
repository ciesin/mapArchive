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
def upload(manifest: str, local_dir: str):
    """Upload map files to Cloudflare R2."""
    from .r2_upload import upload_manifest_files

    rows = load_manifest(manifest)
    click.echo(f"Uploading {len(rows)} files to R2...")
    keys = upload_manifest_files(rows, local_dir)
    click.echo(f"  {len(keys)} files uploaded")


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
