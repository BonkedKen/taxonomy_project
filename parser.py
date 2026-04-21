from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


@dataclass
class NodeRecord:
    taxon_id: int
    parent_taxon_id: int
    rank: str
    division_id: int
    genetic_code_id: int


@dataclass
class NameRecord:
    taxon_id: int
    name_txt: str
    unique_name: str
    name_class: str


def _split_dmp_line(line: str) -> list[str]:
    parts = line.rstrip("\n").split("|")
    return [p.strip() for p in parts]


def parse_nodes(path: str | Path) -> Iterator[NodeRecord]:
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            cols = _split_dmp_line(raw)
            if len(cols) < 5:
                raise ValueError(
                    f"nodes.dmp line {lineno}: expected 5+ fields, got {len(cols)}"
                )
            yield NodeRecord(
                taxon_id=int(cols[0]),
                parent_taxon_id=int(cols[1]),
                rank=cols[2] or "no rank",
                division_id=int(cols[3]) if cols[3].isdigit() else 0,
                genetic_code_id=int(cols[4]) if cols[4].isdigit() else 1,
            )


def parse_names(path: str | Path) -> Iterator[NameRecord]:
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, start=1):
            raw = raw.strip()
            if not raw:
                continue
            cols = _split_dmp_line(raw)
            if len(cols) < 4:
                raise ValueError(
                    f"names.dmp line {lineno}: expected 4+ fields, got {len(cols)}"
                )
            yield NameRecord(
                taxon_id=int(cols[0]),
                name_txt=cols[1],
                unique_name=cols[2],
                name_class=cols[3],
            )