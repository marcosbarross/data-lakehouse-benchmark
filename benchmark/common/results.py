"""Persistência simples, estável e independente de pandas."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Iterable, Mapping, Any


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, default=lambda x: asdict(x) if is_dataclass(x) else str(x),
                               indent=2, ensure_ascii=False), encoding="utf-8")


def load_json(path: Path) -> Any:
    """Carrega dados estruturados de um arquivo JSON."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    materialized = list(rows)
    if not materialized:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Coleta a união ordenada de todas as chaves presentes em qualquer linha
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in materialized:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(materialized)
