"""Brazil SI-PNI / SINASC connector for DATASUS TabNet CSV exports.

Raw files are produced by ``scripts/fetch_tabnet.py`` and are never modified here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from .. import schema
from ..tabnet import read_tabnet_csv
from .base import Connector, LoadResult, QualityReport, SystemBreak


@dataclass(frozen=True)
class FileSpec:
    file: str
    measure: str
    years: tuple[int, ...]
    attribution: str
    system_period: str


LEGACY = "legacy_si_pni_tabnet_1994_2022"

FILES: tuple[FileSpec, ...] = (
    FileSpec("rj_mun_coverage_triplice_viral_d1_2015_2022.csv", "published_coverage_pct",
             tuple(range(2015, 2023)), "as_published", LEGACY),
    FileSpec("rj_mun_doses_triplice_viral_scr_d1_age1_2015_2022.csv", "doses_administered",
             tuple(range(2015, 2023)), "place_of_recording", LEGACY),
    FileSpec("rj_mun_sinasc_live_births_residence_2014_2021.csv", "live_births",
             tuple(range(2014, 2022)), "mother_residence", "sinasc"),
)


class BrazilSIPNIConnector(Connector):
    source_id = "brazil_sipni_tabnet"
    country_iso3 = "BRA"
    system_breaks = (
        SystemBreak(
            2023,
            "old SI-PNI data entry ended 31 May 2023; new SI-PNI module integrated with RNDS "
            "from 1 Jun 2023; TabNet series ends in 2022",
            "confirmed",
        ),
        SystemBreak(
            2024,
            "new national coverage method (RNDS-only numerator, CPF/CNS deduplication)",
            "not directly verified",
        ),
    )

    def __init__(self, raw_dir, admin1_code: str = "33", files: tuple[FileSpec, ...] = FILES):
        super().__init__(raw_dir)
        self.admin1_code = admin1_code
        self.files = files
        self._code_re = re.compile(rf"^{re.escape(admin1_code)}\d{{4}}$")

    def load(self) -> LoadResult:
        self.verify_manifest({f.file for f in self.files})
        quality = QualityReport()
        frames, code_sets, names = [], {}, {}

        for spec in self.files:
            try:
                t = read_tabnet_csv(self.raw_dir / spec.file)
            except (StopIteration, KeyError, ValueError) as e:
                raise schema.SchemaError(f"{spec.file}: not a recognisable TabNet table ({e})") from e

            years = tuple(int(c) for c in t.values.columns)
            if years != spec.years:
                raise schema.SchemaError(f"{spec.file}: years {years} != expected {spec.years}")
            bad = [c for c in t.values.index if not self._code_re.match(c)]
            if bad:
                raise schema.SchemaError(f"{spec.file}: invalid municipality codes {bad[:5]}")
            code_sets[spec.file] = set(t.values.index)
            names.update(t.names)

            for label in t.excluded_rows:
                quality.excluded_rows[f"{spec.file}: {label}"] = (
                    "no municipality code (e.g. residence unknown); excluded, not redistributed")
            for unit, year, raw in t.unparsed_cells:
                quality.missing_values.append((unit, year, spec.measure))

            long = (t.values.rename_axis("unit_code").reset_index()
                    .melt(id_vars="unit_code", var_name="year", value_name="value"))
            long["measure"] = spec.measure
            long["attribution"] = spec.attribution
            long["system_period"] = spec.system_period
            frames.append(long)

        reference = next(iter(code_sets.values()))
        for f, codes in code_sets.items():
            if codes != reference:
                raise schema.SchemaError(f"{f}: municipality set differs from other files "
                                         f"(symmetric difference: {sorted(codes ^ reference)[:5]})")

        obs = pd.concat(frames, ignore_index=True)
        obs["source_id"] = self.source_id
        obs["country_iso3"] = self.country_iso3
        obs["admin1_code"] = self.admin1_code
        obs["unit_name"] = obs["unit_code"].map(names)
        obs = obs.astype({c: t for c, t in schema.COLUMNS.items()})[list(schema.COLUMNS)]
        obs = obs.sort_values(["unit_code", "measure", "year"], ignore_index=True)
        quality.notes.extend(NOTES)
        return LoadResult(schema.validate(obs), quality)


NOTES = [
    "Published coverage uses an unpublished target population (NU_POPULACAO); it is quoted as "
    "published and cannot be exactly reproduced from current SINASC births.",
    "Doses are attributed to the municipality where they were recorded; births to the mother's "
    "residence. Coverage above 100% is expected in some municipalities and is not corrected.",
    "Comparisons must stay within 2015-2022 (legacy SI-PNI). Values are recorded activity, "
    "not confirmed vaccination uptake.",
]
