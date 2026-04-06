"""Manifest parsing and validation using Pydantic."""

import csv
from pathlib import Path

from pydantic import BaseModel, field_validator


class ManifestRow(BaseModel):
    """A single row in the map manifest CSV."""

    drive_file_id: str
    filename: str
    theme: str
    page_size: str = ""
    page_num: str = ""
    admin0: str          # ISO 3166-1 alpha-3 — always required
    admin1: str = ""     # Province / state
    admin2: str = ""     # District / territory
    admin3: str = ""     # Sub-district / commune
    admin4: str = ""     # Village / locality
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

    @field_validator("admin0")
    @classmethod
    def validate_admin0(cls, v: str) -> str:
        if len(v) != 3 or not v.isalpha():
            raise ValueError(
                f"admin0 must be a 3-letter ISO 3166-1 alpha-3 code, got '{v}'"
            )
        return v.upper()

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
        """STAC item ID: filename stem, which is unique and self-describing.

        Strips the extension and replaces any characters that must be
        percent-encoded in a URL with hyphens (spaces, brackets, etc.).
        Underscores and hyphens are preserved — they're unreserved URI chars.
        """
        stem = Path(self.filename).stem
        # Replace anything that isn't an unreserved URI character
        import re
        return re.sub(r"[^A-Za-z0-9\-._~]", "-", stem)

    @property
    def r2_key(self) -> str:
        """R2 object path: maps/{theme}/{admin0}/{admin1}/.../{filename}"""
        admin_subpath = "/".join(self.admin_path)
        return f"maps/{self.theme}/{admin_subpath}/{self.filename}"


def load_manifest(path: str | Path) -> list[ManifestRow]:
    """Load and validate a manifest CSV file."""
    path = Path(path)
    rows: list[ManifestRow] = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, raw in enumerate(reader, start=2):
            try:
                rows.append(ManifestRow(**raw))
            except Exception as e:
                raise ValueError(f"Manifest row {i}: {e}") from e
    return rows
