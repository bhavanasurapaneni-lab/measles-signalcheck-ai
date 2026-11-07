"""Read DATASUS TabNet CSV exports (raw files are never modified).

TabNet exports are Latin-1, semicolon-separated, with Brazilian number formatting
("1.234" thousands, "98,72" decimals), a "Total" row/column, and (for SINASC) title
and footnote lines around the table. This module returns a tidy wide table:
index = 6-digit IBGE municipality code, columns = years, plus a separate name map.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

MUNICIPALITY_ROW = re.compile(r"^(\d{6}) (.+)$")


@dataclass
class TabnetTable:
    values: pd.DataFrame                      # index: IBGE code (str), columns: year (int)
    names: dict[str, str]                     # IBGE code -> municipality name
    total_row: dict[int, float]               # TabNet's own "Total" row (for checks only)
    excluded_rows: dict[str, list] = field(default_factory=dict)  # e.g. "MUNICIPIO IGNORADO"
    header_lines: list[str] = field(default_factory=list)
    footer_lines: list[str] = field(default_factory=list)
    unparsed_cells: list[tuple[str, int, str]] = field(default_factory=list)


def _to_number(cell: str) -> float | None:
    s = str(cell).strip().strip('"')
    if s in ("", "-", "..."):
        return None
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def read_tabnet_csv(path: str | Path) -> TabnetTable:
    lines = Path(path).read_text(encoding="latin-1").splitlines()
    start = next(i for i, l in enumerate(lines) if l.lstrip().startswith('"Munic'))
    end = next(i for i in range(start, len(lines)) if lines[i].strip().strip('"').startswith("Total"))
    table = pd.read_csv(io.StringIO("\n".join(lines[start:end + 1])), sep=";", dtype=str,
                        keep_default_na=False)
    table.columns = [c.strip() for c in table.columns]
    year_cols = [c for c in table.columns if re.fullmatch(r"\d{4}", c)]

    values, names, excluded, unparsed = {}, {}, {}, []
    total_row: dict[int, float] = {}
    for _, row in table.iterrows():
        label = row["Município"].strip()
        nums = {}
        for c in year_cols:
            v = _to_number(row[c])
            if v is None:
                unparsed.append((label, int(c), row[c]))
            nums[int(c)] = v
        if label == "Total":
            total_row = nums
            continue
        m = MUNICIPALITY_ROW.match(label)
        if not m:
            excluded[label] = [nums[int(c)] for c in year_cols]
            continue
        code, name = m.groups()
        values[code] = nums
        names[code] = name.strip()

    df = pd.DataFrame.from_dict(values, orient="index").sort_index()
    df.index.name = "ibge_code"
    return TabnetTable(
        values=df, names=names, total_row=total_row, excluded_rows=excluded,
        header_lines=[l for l in lines[:start] if l.strip()],
        footer_lines=[l.strip() for l in lines[end + 1:] if l.strip()],
        unparsed_cells=[u for u in unparsed if u[0] != "Total"],
    )
