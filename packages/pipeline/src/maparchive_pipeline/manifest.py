"""Manifest parsing and validation using Pydantic."""

import csv
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, field_validator


class ManifestRow(BaseModel):
    """A single row in the map manifest CSV."""

    drive_file_id: str
    filename: str
    admin_tree: str
    theme: str
    use_case: str = ""
    admin_level: int = 0  # 0 = admin0 only, 1 = admin0+admin1, etc.
    page_size: str = ""
    page_num: str = ""
    admin0: str          # ISO 3166-1 alpha-3 — always required
    admin1: str = ""     # Province / state / etc
    admin2: str = ""     # Antenne / district
    admin3: str = ""     # Zone de santé
    admin4: str = ""     # Aire de santé
    title: str
    description: str = ""
    date: str            # ISO 8601, e.g. "2024-01-01"
    bbox_west: float
    bbox_south: float
    bbox_east: float
    bbox_north: float
    keywords: str = ""   # comma-separated
    license: str = "CC-BY-4.0"
    source_attribution: str = ""
    # Populated by enrich step
    spatial_level: str = ""  # e.g. "zonesante", "airesante"
    grid3id: str = ""        # GRID3 boundary identifier

    @field_validator("admin0")
    @classmethod
    def validate_admin0(cls, v: str) -> str:
        if len(v) != 3 or not v.isalpha():
            raise ValueError(
                f"admin0 must be a 3-letter ISO 3166-1 alpha-3 code, got '{v}'"
            )
        return v.upper()

    @property
    def filename_normalized(self) -> str:
        """Filename reconstructed in the canonical NEW convention.

        {pageSize}_{useCase}_{admin0}[_{admin1..N}][_{pageNum}]_{YYYYMMDD}.{ext}

        All parts are lowercase for stable, case-consistent permanent URLs.
        Legacy filenames (different convention or use_case) are fully re-expressed.
        """
        ext = Path(self.filename).suffix.lower()
        parts = [self.page_size.lower(), self.use_case]
        parts += [a.lower() for a in self.admin_path]
        if self.page_num:
            parts.append(self.page_num)
        parts.append(self.date.replace("-", ""))  # YYYY-MM-DD → YYYYMMDD
        return "_".join(parts) + ext

    @property
    def keyword_list(self) -> list[str]:
        if not self.keywords:
            return []
        return [k.strip() for k in self.keywords.split(",") if k.strip()]

    @property
    def bbox(self) -> list[float]:
        return [self.bbox_west, self.bbox_south, self.bbox_east, self.bbox_north]

    @property
    def admin_path(self) -> list[str]:
        """Ordered list of non-empty admin levels, from admin0 inward."""
        return [a for a in [self.admin0, self.admin1, self.admin2, self.admin3, self.admin4] if a]

    @property
    def deepest_admin(self) -> str:
        """The most granular admin level present."""
        return self.admin_path[-1]

    @property
    def item_id(self) -> str:
        """STAC item ID derived from the normalized filename stem.

        Uses filename_normalized so legacy and new-convention items share a
        consistent ID format.  STAC-safe: lowercase [a-z0-9-._~] only.
        """
        import re
        stem = Path(self.filename_normalized).stem
        return re.sub(r"[^a-z0-9\-._~]", "-", stem.lower())

    @property
    def collection_id(self) -> str:
        """STAC collection ID for this item's AOI: lowercase, hyphen-joined admin path.

        e.g. admin_path ["COD", "Tshopo", "Kisangani"] → "cod-tshopo-kisangani"
        """
        return "-".join(a.lower() for a in self.admin_path)

    @property
    def r2_key(self) -> str:
        """R2 object path: maps/{theme}/{admin_path...}/{use_case}/{filename_normalized}"""
        admin_subpath = "/".join(a.lower() for a in self.admin_path)
        use_case_slug = self.use_case.lower() if self.use_case else "uncategorized"
        return f"maps/{self.theme}/{admin_subpath}/{use_case_slug}/{self.filename_normalized}"


def load_manifest(path: str | Path) -> list[ManifestRow]:
    """Load and validate a manifest CSV file."""
    path = Path(path)
    rows: list[ManifestRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            try:
                row_data = cast(dict[str, Any], raw)
                rows.append(ManifestRow.model_validate(row_data))
            except Exception as e:
                raise ValueError(f"Manifest row {i}: {e}") from e
    return rows
