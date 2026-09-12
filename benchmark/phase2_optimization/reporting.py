"""Gráfico e relatório da Fase 2."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt


def create_artifacts(rows: list[dict[str, Any]], output_dir: Path) -> None:
    successful = [r for r in rows if not r["error"]]
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in successful:
        grouped[(row["catalog"], row["query"]) + (row["variant"],)].append(row["elapsed_seconds"])
    summaries = []
    for (catalog, query, variant), values in grouped.items():
        summaries.append({"catalog": catalog, "query": query, "variant": variant,
                          "mean_seconds": sum(values) / len(values)})
    (output_dir / "summary.md").write_text(_markdown(summaries), encoding="utf-8")
    _plot(summaries, output_dir / "speedup.png")


def _markdown(summaries: list[dict[str, Any]]) -> str:
    lines = ["# Fase 2 — Otimização de leitura", "", "| Formato | Query | Controle (s) | Otimizada (s) | Speedup |", "|---|---|---:|---:|---:|"]
    values = {(r["catalog"], r["query"], r["variant"]): r["mean_seconds"] for r in summaries}
    for catalog, query in sorted({(r["catalog"], r["query"]) for r in summaries}):
        control, optimized = values.get((catalog, query, "control")), values.get((catalog, query, "optimized"))
        speedup = control / optimized if control and optimized else None
        lines.append(f"| {catalog} | {query} | {control or 'N/A'} | {optimized or 'N/A'} | {f'{speedup:.2f}x' if speedup else 'N/A'} |")
    lines.extend(["", "`EXPLAIN ANALYZE` bruto está salvo em `plans/`; as métricas dependem da versão do Trino."])
    return "\n".join(lines) + "\n"


def _plot(summaries: list[dict[str, Any]], path: Path) -> None:
    labels, values = [], []
    for item in summaries:
        labels.append(f"{item['catalog']}\n{item['query']}\n{item['variant']}")
        values.append(item["mean_seconds"])
    if not values:
        return
    figure, axis = plt.subplots(figsize=(max(10, len(labels) * 1.1), 6))
    axis.bar(range(len(values)), values, color=["#1f77b4" if "iceberg" in x else "#ff7f0e" for x in labels])
    axis.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    axis.set_ylabel("Tempo médio (s)")
    axis.set_title("Fase 2: controle versus otimização")
    axis.grid(axis="y", alpha=.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
