"""Minimal connector contract.

A connector turns one public source's raw files into canonical observations
(see ``signalcheck.schema``) plus a data-quality report. Adding a new dataset means
writing one new subclass; nothing downstream changes.
"""
from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


class ManifestError(RuntimeError):
    """Raw files are missing, altered, or not described by the manifest."""


class ComparabilityError(ValueError):
    """A requested comparison crosses a known reporting-system break."""


@dataclass(frozen=True)
class SystemBreak:
    year: int          # first year of the new system
    description: str
    evidence: str      # "confirmed" or "not directly verified"


@dataclass
class QualityReport:
    """Facts about the source data. Nothing here is imputed or corrected."""
    excluded_rows: dict[str, str] = field(default_factory=dict)       # label -> reason
    missing_values: list[tuple[str, int, str]] = field(default_factory=list)  # (unit, year, measure)
    notes: list[str] = field(default_factory=list)


@dataclass
class LoadResult:
    observations: pd.DataFrame
    quality: QualityReport


class Connector(ABC):
    source_id: str
    system_breaks: tuple[SystemBreak, ...] = ()

    def __init__(self, raw_dir: str | Path):
        self.raw_dir = Path(raw_dir)

    # --- provenance -------------------------------------------------------------
    def verify_manifest(self, expected_files: set[str]) -> dict:
        """Check every expected raw file exists and matches its manifest hash."""
        path = self.raw_dir / "manifest.json"
        if not path.exists():
            raise ManifestError(f"manifest not found: {path}")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        entries = {e["file"]: e for e in manifest.get("files", [])}
        missing_entries = expected_files - set(entries)
        if missing_entries:
            raise ManifestError(f"manifest lacks entries for: {sorted(missing_entries)}")
        for name in sorted(expected_files):
            f = self.raw_dir / name
            if not f.exists():
                raise ManifestError(f"raw file missing: {f}")
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            if digest != entries[name]["sha256"]:
                raise ManifestError(f"raw file altered (hash mismatch): {name}")
        return manifest

    # --- comparability ----------------------------------------------------------
    def check_comparable(self, year_a: int, year_b: int) -> None:
        """Raise if two years fall on different sides of a reporting-system break."""
        lo, hi = sorted((year_a, year_b))
        for b in self.system_breaks:
            if lo < b.year <= hi:
                raise ComparabilityError(
                    f"{lo} and {hi} straddle a reporting-system break in {b.year}: "
                    f"{b.description} ({b.evidence})"
                )

    @abstractmethod
    def load(self) -> LoadResult:
        """Verify provenance, parse raw files, return validated canonical observations."""
