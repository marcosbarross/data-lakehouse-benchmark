"""Geração de gráficos comparativos e relatório Markdown para o Baseline (Fase 1)."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from benchmark.common.config import TrinoSettings
from benchmark.phase1_baseline.queries import TPCH_QUERIES

CATALOGS = ["iceberg", "delta_lake"]


def generate_plots(results: dict[str, Any], output_dir: Path) -> Path:
    """Gera gráficos comparativos em alta resolução."""
    output_dir.mkdir(parents=True, exist_ok=True)

    queries = sorted(TPCH_QUERIES.keys(), key=lambda x: int(x[1:]))
    common_queries = [q for q in queries if all(q in results.get(cat, {}) for cat in CATALOGS)]

    if not common_queries:
        print("[AVISO] Nenhuma consulta comum aos catálogos encontrada para geração de gráficos.")
        return output_dir

    # Gráfico 1: Comparação lado a lado (barras agrupadas)
    x = range(len(common_queries))
    width = 0.35

    fig, ax = plt.subplots(figsize=(16, 7))

    iceberg_times = [results["iceberg"][q]["avg_time"] for q in common_queries]
    delta_times = [results["delta_lake"][q]["avg_time"] for q in common_queries]

    bars1 = ax.bar([i - width / 2 for i in x], iceberg_times, width,
                   label="Iceberg", color="#1f77b4", alpha=0.85)
    bars2 = ax.bar([i + width / 2 for i in x], delta_times, width,
                   label="Delta Lake", color="#ff7f0e", alpha=0.85)

    ax.set_xlabel("Queries TPC-H", fontsize=12)
    ax.set_ylabel("Tempo Médio de Execução (segundos)", fontsize=12)
    ax.set_title("Comparação de Performance: Iceberg vs Delta Lake (TPC-H SF1)", fontsize=14)
    ax.set_xticks(list(x))
    ax.set_xticklabels(common_queries, rotation=45)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    for bar in bars1:
        h = bar.get_height()
        ax.annotate(f"{h:.2f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8)
    for bar in bars2:
        h = bar.get_height()
        ax.annotate(f"{h:.2f}", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_dir / "iceberg_vs_deltalake.png", dpi=300, bbox_inches="tight")
    plt.close()

    # Gráfico 2: Speedup do Delta Lake em relação ao Iceberg
    speedup = []
    for q in common_queries:
        iceberg_t = results["iceberg"][q]["avg_time"]
        delta_t = results["delta_lake"][q]["avg_time"]
        speedup.append(iceberg_t / delta_t if delta_t > 0 else 0)

    fig, ax = plt.subplots(figsize=(14, 6))
    colors = ["#2ca02c" if s > 1 else "#d62728" for s in speedup]
    bars = ax.bar(common_queries, speedup, color=colors, alpha=0.85)
    ax.axhline(y=1.0, color="black", linestyle="--", linewidth=1, label="Paridade (1.0x)")
    ax.set_xlabel("Queries TPC-H", fontsize=12)
    ax.set_ylabel("Speedup (Iceberg / Delta Lake)", fontsize=12)
    ax.set_title("Speedup do Delta Lake em relação ao Iceberg (>1 = Delta Lake mais rápido)",
                 fontsize=13)
    ax.set_xticks(range(len(common_queries)))
    ax.set_xticklabels(common_queries, rotation=45)
    ax.legend()
    ax.grid(axis="y", alpha=0.3)

    for bar, s in zip(bars, speedup):
        h = bar.get_height()
        ax.annotate(f"{s:.2f}x", xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", va="bottom", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / "speedup_deltalake_vs_iceberg.png", dpi=300, bbox_inches="tight")
    plt.close()

    # Gráfico 3: Tempo total acumulado
    total_iceberg = sum(results["iceberg"][q]["avg_time"] for q in common_queries)
    total_delta = sum(results["delta_lake"][q]["avg_time"] for q in common_queries)

    fig, ax = plt.subplots(figsize=(8, 6))
    bars = ax.bar(["Iceberg", "Delta Lake"], [total_iceberg, total_delta],
                  color=["#1f77b4", "#ff7f0e"], alpha=0.85)
    ax.set_ylabel("Tempo Total Acumulado (segundos)", fontsize=12)
    ax.set_title(f"Tempo Total Acumulado — {len(common_queries)} Queries TPC-H", fontsize=14)
    for bar, t in zip(bars, [total_iceberg, total_delta]):
        ax.text(bar.get_x() + bar.get_width() / 2.0, bar.get_height(),
                f"{t:.2f}s", ha="center", va="bottom", fontsize=12, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "total_time_comparison.png", dpi=300, bbox_inches="tight")
    plt.close()

    return output_dir


def generate_markdown_report(
    results: dict[str, Any],
    output_dir: Path,
    settings: TrinoSettings,
    report_path: Path | None = None,
    schema: str = "benchmark",
) -> Path:
    """Gera relatório comparativo em Markdown atualizado com a infraestrutura OpenTofu."""
    queries = sorted(TPCH_QUERIES.keys(), key=lambda x: int(x[1:]))
    common_queries = [q for q in queries if all(q in results.get(cat, {}) for cat in CATALOGS)]

    target_report = report_path or (Path("benchmark_report.md"))

    report: list[str] = []
    report.append("# Benchmark Comparativo - Iceberg vs Delta Lake")
    report.append(f"\n**Data:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n## Configuração do Ambiente\n")
    report.append(f"- **Host Trino:** `{settings.host}:{settings.port}`")
    report.append(f"- **Schema de Benchmark:** `{schema}`")
    report.append(f"- **Iterações por Query:** {settings.iterations}")
    report.append("- **Catálogo Iceberg:** Apache Iceberg (S3/MinIO)")
    report.append("- **Catálogo Delta Lake:** Delta Lake (S3/MinIO)")
    report.append("- **Infraestrutura:** Cluster K3s gerenciado via **OpenTofu** (Magalu Cloud) — Topologia de 6 Nós:")
    report.append("  - `lakehouse-k3s-master` (BV2-4-40: 2 vCPUs, 4 GB RAM) — K3s Control Plane & Trino Coordinator")
    report.append("  - `lakehouse-k3s-worker1` (BV4-8-40: 4 vCPUs, 8 GB RAM) — MinIO Dedicated Object Storage (Taint dedicado)")
    report.append("  - `lakehouse-k3s-worker5` (BV2-4-40: 2 vCPUs, 4 GB RAM) — Dedicated Metadata Catalogs (PostgreSQL + Hive Metastore)")
    report.append("  - `lakehouse-k3s-worker2` (BV4-16-100: 4 vCPUs, 16 GB RAM) — Trino Compute Worker 1 (12 GB JVM Heap)")
    report.append("  - `lakehouse-k3s-worker3` (BV4-16-100: 4 vCPUs, 16 GB RAM) — Trino Compute Worker 2 (12 GB JVM Heap)")
    report.append("  - `lakehouse-k3s-worker4` (BV4-16-100: 4 vCPUs, 16 GB RAM) — Trino Compute Worker 3 (12 GB JVM Heap)")
    report.append("- **Dataset:** TPC-H SF1 (~1GB gerado sinteticamente)")


    if not common_queries:
        report.append("\n## Resultados\n\nNenhuma consulta com execução completa em ambos os catálogos.")
        target_report.write_text("\n".join(report), encoding="utf-8")
        return target_report

    report.append("\n## Visão Geral dos Resultados\n")
    total_iceberg = sum(results["iceberg"][q]["avg_time"] for q in common_queries)
    total_delta = sum(results["delta_lake"][q]["avg_time"] for q in common_queries)

    winner = "Delta Lake" if total_delta < total_iceberg else "Iceberg"
    diff_pct = abs(total_iceberg - total_delta) / max(total_iceberg, total_delta) * 100

    report.append(f"- **Tempo total Iceberg:** {total_iceberg:.2f}s")
    report.append(f"- **Tempo total Delta Lake:** {total_delta:.2f}s")
    report.append(f"- **Melhor performer geral:** {winner} ({diff_pct:.1f}% mais rápido)")

    report.append("\n## Tabela Comparativa Detalhada\n")
    report.append("| Query | Iceberg (s) | Delta Lake (s) | Speedup Delta | Vencedor |")
    report.append("|-------|-------------|----------------|---------------|----------|")

    delta_wins = 0
    iceberg_wins = 0

    for q in common_queries:
        i_t = results["iceberg"][q]["avg_time"]
        d_t = results["delta_lake"][q]["avg_time"]
        speedup = i_t / d_t if d_t > 0 else 0
        winner_q = "Delta Lake" if d_t < i_t else "Iceberg"
        if d_t < i_t:
            delta_wins += 1
        else:
            iceberg_wins += 1
        report.append(f"| {q} | {i_t:.2f} | {d_t:.2f} | {speedup:.2f}x | {winner_q} |")

    report.append(f"\n**Resumo:** Delta Lake venceu em {delta_wins} queries, "
                  f"Iceberg venceu em {iceberg_wins} queries.")

    import os
    img1 = os.path.relpath(output_dir / "iceberg_vs_deltalake.png", target_report.parent)
    img2 = os.path.relpath(output_dir / "speedup_deltalake_vs_iceberg.png", target_report.parent)
    img3 = os.path.relpath(output_dir / "total_time_comparison.png", target_report.parent)

    report.append("\n## Gráficos\n")
    report.append("### Comparação de Tempo Médio por Query\n")
    report.append(f"![Iceberg vs Delta Lake]({img1})\n")

    report.append("### Speedup Relativo do Delta Lake em Relação ao Iceberg\n")
    report.append(f"![Speedup]({img2})\n")

    report.append("### Tempo Total Acumulado\n")
    report.append(f"![Tempo Total]({img3})\n")

    report.append("## Estatísticas Descritivas\n")
    report.append("\n### Iceberg\n")
    report.append("| Query | Média (s) | Mín (s) | Máx (s) | Desvio Padrão (s) |")
    report.append("|-------|-----------|---------|---------|-------------------|")
    for q in common_queries:
        r = results["iceberg"][q]
        report.append(f"| {q} | {r['avg_time']:.2f} | {r['min_time']:.2f} | "
                      f"{r['max_time']:.2f} | {r['std_dev']:.2f} |")

    report.append("\n### Delta Lake\n")
    report.append("| Query | Média (s) | Mín (s) | Máx (s) | Desvio Padrão (s) |")
    report.append("|-------|-----------|---------|---------|-------------------|")
    for q in common_queries:
        r = results["delta_lake"][q]
        report.append(f"| {q} | {r['avg_time']:.2f} | {r['min_time']:.2f} | "
                      f"{r['max_time']:.2f} | {r['std_dev']:.2f} |")

    report.append("\n## Conclusão\n")
    report.append(f"Neste benchmark com {len(common_queries)} queries do TPC-H executadas "
                  f"{settings.iterations} vezes cada, o **{winner}** apresentou melhor performance "
                  f"geral, sendo {diff_pct:.1f}% mais rápido que o concorrente no tempo acumulado.")
    report.append("\nObservações:")
    report.append("- As tabelas foram criadas em ambos os catálogos a partir do dataset "
                  f"sintético {settings.source_catalog}.{settings.source_schema} (~1GB).")
    report.append("- O staging e a execução foram orquestrados de forma automatizada em Python.")
    report.append("- Os dados residem no MinIO em formato Parquet, gerenciados pelos "
                  "respectivos metadados de cada engine lakehouse.")
    report.append("- Infraestrutura de máquinas virtuais na nuvem provisionada pelo OpenTofu.")

    target_report.parent.mkdir(parents=True, exist_ok=True)
    target_report.write_text("\n".join(report), encoding="utf-8")
    print(f"\n[OK] Relatório gerado: {target_report}")
    return target_report
