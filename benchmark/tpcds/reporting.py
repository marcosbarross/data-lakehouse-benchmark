"""Geração de gráficos comparativos e relatório Markdown para a suíte TPC-DS."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from benchmark.common.config import TrinoSettings
from benchmark.tpcds.queries import TPCDS_QUERIES

CATALOGS = ["iceberg", "delta_lake"]


def generate_plots(results: dict[str, Any], output_dir: Path, scale_factor: str = "sf1") -> Path:
    """Gera gráficos comparativos da suíte TPC-DS."""
    output_dir.mkdir(parents=True, exist_ok=True)

    queries = sorted(TPCDS_QUERIES.keys())
    common_queries = [q for q in queries if all(q in results.get(cat, {}) for cat in CATALOGS)]

    if not common_queries:
        print("[AVISO] Nenhuma consulta comum aos catálogos encontrada para geração de gráficos TPC-DS.")
        return output_dir

    x = range(len(common_queries))
    width = 0.35

    # Gráfico 1: Comparação lado a lado
    fig, ax = plt.subplots(figsize=(14, 6))
    iceberg_times = [results["iceberg"][q]["avg_time"] for q in common_queries]
    delta_times = [results["delta_lake"][q]["avg_time"] for q in common_queries]

    bars1 = ax.bar([i - width / 2 for i in x], iceberg_times, width,
                   label="Iceberg", color="#1f77b4", alpha=0.85)
    bars2 = ax.bar([i + width / 2 for i in x], delta_times, width,
                   label="Delta Lake", color="#ff7f0e", alpha=0.85)

    ax.set_xlabel("Queries TPC-DS", fontsize=12)
    ax.set_ylabel("Tempo Médio de Execução (s)", fontsize=12)
    ax.set_title(f"Comparação de Performance TPC-DS ({scale_factor.upper()}): Iceberg vs Delta Lake", fontsize=14)
    ax.set_xticks(list(x))
    ax.set_xticklabels(common_queries, rotation=0)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    for bar in bars1:
        h = bar.get_height()
        ax.annotate(f"{h:.2f}s", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        h = bar.get_height()
        ax.annotate(f"{h:.2f}s", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plot1_path = output_dir / "tpcds_iceberg_vs_deltalake.png"
    plt.savefig(plot1_path, dpi=300)
    plt.close()

    # Gráfico 2: Speedup Delta Lake vs Iceberg
    speedups = [
        results["iceberg"][q]["avg_time"] / results["delta_lake"][q]["avg_time"]
        if results["delta_lake"][q]["avg_time"] > 0 else 1.0
        for q in common_queries
    ]

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ["#2ca02c" if s >= 1.0 else "#d62728" for s in speedups]
    bars = ax.bar(x, speedups, width=0.5, color=colors, alpha=0.85)

    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1, alpha=0.7)
    ax.set_xlabel("Queries TPC-DS", fontsize=12)
    ax.set_ylabel("Speedup (Iceberg / Delta Lake)", fontsize=12)
    ax.set_title(f"Speedup Relativo do Delta Lake sobre o Iceberg - TPC-DS ({scale_factor.upper()})", fontsize=14)
    ax.set_xticks(list(x))
    ax.set_xticklabels(common_queries, rotation=0)
    ax.grid(axis="y", alpha=0.3)

    for bar, s in zip(bars, speedups):
        ax.annotate(f"{s:.2f}x", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom",
                    fontsize=9, fontweight="bold")

    plt.tight_layout()
    plot2_path = output_dir / "tpcds_speedup.png"
    plt.savefig(plot2_path, dpi=300)
    plt.close()

    return output_dir


def generate_markdown_report(
    results: dict[str, Any],
    settings: TrinoSettings,
    report_path: Path,
    plots_dir: Path,
    schema: str,
) -> Path:
    """Gera relatório Markdown consolidado do TPC-DS."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    queries = sorted(TPCDS_QUERIES.keys())
    common_queries = [q for q in queries if all(q in results.get(cat, {}) for cat in CATALOGS)]

    if not common_queries:
        return report_path

    total_iceberg = sum(results["iceberg"][q]["avg_time"] for q in common_queries)
    total_delta = sum(results["delta_lake"][q]["avg_time"] for q in common_queries)
    overall_speedup = total_iceberg / total_delta if total_delta > 0 else 1.0
    overall_winner = "Delta Lake" if total_delta < total_iceberg else "Iceberg"
    overall_pct = abs((total_iceberg - total_delta) / max(total_iceberg, total_delta)) * 100

    table_rows: list[str] = []
    iceberg_wins = 0
    delta_wins = 0

    for q in common_queries:
        ti = results["iceberg"][q]["avg_time"]
        td = results["delta_lake"][q]["avg_time"]
        speedup = ti / td if td > 0 else 1.0
        if td < ti:
            winner = "Delta Lake"
            delta_wins += 1
        elif ti < td:
            winner = "Iceberg"
            iceberg_wins += 1
        else:
            winner = "Empate"

        table_rows.append(f"| {q} | {ti:.2f} | {td:.2f} | {speedup:.2f}x | {winner} |")

    lines = [
        f"# Benchmark TPC-DS (Decision Support) - Iceberg vs Delta Lake",
        "",
        f"**Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## Configuração do Ambiente",
        "",
        f"- **Host Trino:** `{settings.host}:{settings.port}`",
        f"- **Workload:** TPC-DS ({settings.scale_factor.upper()})",
        f"- **Schema no Lakehouse:** `{schema}`",
        f"- **Iterações por Query:** {settings.iterations}",
        f"- **Catálogos Avaliados:** Apache Iceberg vs Delta Lake (armazenamento MinIO S3)",
        "",
        "## Visão Geral dos Resultados",
        "",
        f"- **Tempo total Iceberg:** {total_iceberg:.2f}s",
        f"- **Tempo total Delta Lake:** {total_delta:.2f}s",
        f"- **Melhor performer geral:** {overall_winner} ({overall_pct:.1f}% mais rápido)",
        f"- **Placar de Vitórias:** Delta Lake: {delta_wins} | Iceberg: {iceberg_wins}",
        "",
        "## Tabela Comparativa Detalhada",
        "",
        "| Query | Iceberg (s) | Delta Lake (s) | Speedup Delta | Vencedor |",
        "|---|---|---|---|---|",
        *table_rows,
        "",
        "## Gráficos",
        "",
        f"![Comparação TPC-DS]({os.path.relpath(plots_dir / 'tpcds_iceberg_vs_deltalake.png', report_path.parent)})",
        "",
        f"![Speedup TPC-DS]({os.path.relpath(plots_dir / 'tpcds_speedup.png', report_path.parent)})",
        "",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path
