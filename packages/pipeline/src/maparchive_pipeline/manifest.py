"""Manifest parsing and validation using Pydantic."""

import csv
from pathlib import Path

from pydantic import BaseModel, field_validator


class ManifestRow(BaseModel):
    """A single row in the map manifest CSV."""

    drive_file_id: str
    filename: str
    theme: str
    admin0: str  # ISO 3166-1 alpha-3
    area: str
    title: str
    description: str = ""
    date: str  # ISO 8601 date string, e.g. "2024-01-01"
    bbox_west: float
    bbox_south: float
    bbox_east: float
    bbox_north: float
    keywords: str = ""  # comma-separated
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
    def item_id(self) -> str:
        """Generate a STAC item ID from theme, admin0, area, and filename."""
        stem = Path(self.filename).stem
        area_slug = self.area.lower().replace(" ", "-")
        return f"{self.theme}-{self.admin0.lower()}-{area_slug}-{stem}"

    @property
    def r2_key(self) -> str:
        """R2 object path: maps/{theme}/{admin0}/{area}/{filename}"""
        return f"maps/{self.theme}/{self.admin0}/{self.area}/{self.filename}"


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
