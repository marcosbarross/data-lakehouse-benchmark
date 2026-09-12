"""Módulo de geração de relatórios e visualizações científicas consolidadas.

Consolida os resultados dos benchmarks em 4 figuras analíticas integradas:
1. Visão Geral Executiva (1_executive_overview.png): Tempo Total, Média Geométrica, Speedup % e Escalabilidade Log-Log.
2. Detalhe por Consulta (2_query_divergence.png): Barras horizontais divergentes ordenadas por magnitude de vantagem.
3. Distribuição e Dispersão (3_distribution_and_scatter.png): Boxplots em escala logarítmica e Scatter com paridade y=x e marcadores por escala.
4. Infraestrutura e Estabilidade (4_infrastructure_and_stability.png): I/O MinIO, Latência de Catálogo, CPU e Coeficiente de Variação (CV).

Convenção Semântica de Cores:
- VERDE (#2ca02c): Delta Lake mais rápido / vencedor naquele ponto de dado.
- VERMELHO (#d62728): Apache Iceberg mais rápido / vencedor naquele ponto de dado.
- CINZA NEUTRO (#7f7f7f / #4f5b66): Métricas de infraestrutura sem relação direta de vitória.
"""
from __future__ import annotations

import math
import os
import re
import statistics
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

# Estilo gráfico moderno e sóbrio para publicações acadêmicas
plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 10,
    "figure.titlesize": 13,
})

# Cores semânticas dinâmicas
COLOR_DELTA_WIN = "#2ca02c"    # Verde: Delta Lake venceu / mais rápido
COLOR_ICEBERG_WIN = "#d62728"  # Vermelho: Iceberg venceu / mais rápido
COLOR_NEUTRAL_1 = "#4f5b66"    # Cinza ardósia escuro
COLOR_NEUTRAL_2 = "#8ca0b3"    # Cinza azulado claro


def natural_sort_key(q: str) -> tuple[int, str]:
    """Ordenação natural para consultas como Q1, Q2, ..., Q10, ..., Q99."""
    digits = re.findall(r"\d+", q)
    num = int(digits[0]) if digits else 0
    return (num, q)


def geometric_mean(values: list[float]) -> float:
    """Calcula a média geométrica dos tempos de execução."""
    positives = [v for v in values if v > 0]
    if not positives:
        return 0.0
    return math.exp(sum(math.log(v) for v in positives) / len(positives))


def calc_advantage_pct(time_iceberg: float, time_delta: float) -> float:
    """Calcula a porcentagem de vantagem do Delta Lake sobre o Iceberg.
    
    - Positivo: Delta Lake mais rápido (% mais rápido que o Iceberg).
    - Negativo: Iceberg mais rápido (% mais rápido que o Delta Lake).
    """
    if time_iceberg <= 0 or time_delta <= 0:
        return 0.0
    if time_delta <= time_iceberg:
        return ((time_iceberg - time_delta) / time_iceberg) * 100.0
    else:
        return -(((time_delta - time_iceberg) / time_delta) * 100.0)


def generate_consolidated_report(
    all_runs: list[dict[str, Any]],
    output_dir: Path,
    report_path: Path,
) -> Path:
    """Gera as 4 figuras consolidadas e renderiza o relatório Markdown mestre."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    valid_runs = [r for r in all_runs if not r.get("error")]
    if not valid_runs:
        print("[AVISO] Nenhum registro de execução bem-sucedido para geração de relatórios.")
        return report_path

    # Gera as 4 figuras consolidadas
    try:
        _plot_executive_overview(valid_runs, output_dir)
        _plot_query_divergence(valid_runs, output_dir)
        _plot_distribution_and_scatter(valid_runs, output_dir)
        _plot_infrastructure_and_stability(valid_runs, output_dir)
    except Exception as exc:
        print(f"[AVISO] Falha na renderização de gráficos: {exc}")
        import traceback
        traceback.print_exc()

    # Renderiza o documento Markdown consolidado
    _render_master_markdown(valid_runs, output_dir, report_path)
    return report_path


# ==============================================================================
# FIGURA 1: VISÃO GERAL EXECUTIVA (1_executive_overview.png)
# ==============================================================================
def _plot_executive_overview(runs: list[dict[str, Any]], output_dir: Path) -> None:
    """Unifica Tempo Total Acumulado, Média Geométrica, Speedup % e Escalabilidade."""
    baseline_runs = [r for r in runs if r.get("suite") != "phase2_optimization"]
    groups = sorted(list({(r.get("benchmark", "tpch"), r.get("scale_factor", "sf1")) for r in baseline_runs}))
    if not groups:
        groups = sorted(list({(r.get("benchmark", "tpch"), r.get("scale_factor", "sf1")) for r in runs}))

    group_labels = [f"{b.upper()}\n({sf.upper()})" for b, sf in groups]
    catalogs = ["iceberg", "delta_lake"]

    totals: dict[str, list[float]] = {cat: [] for cat in catalogs}
    gmeans: dict[str, list[float]] = {cat: [] for cat in catalogs}
    speedups: list[float] = []

    for b, sf in groups:
        sub_runs = [r for r in baseline_runs if r.get("benchmark") == b and r.get("scale_factor") == sf]
        queries = sorted(list({r["query"] for r in sub_runs}), key=natural_sort_key)
        cat_avgs: dict[str, list[float]] = {cat: [] for cat in catalogs}
        for cat in catalogs:
            for q in queries:
                q_times = [r["elapsed_seconds"] for r in sub_runs if r["catalog"] == cat and r["query"] == q]
                if q_times:
                    cat_avgs[cat].append(statistics.mean(q_times))
            totals[cat].append(sum(cat_avgs[cat]))
            gmeans[cat].append(geometric_mean(cat_avgs[cat]))

        tot_i = totals["iceberg"][-1]
        tot_d = totals["delta_lake"][-1]
        speedups.append(calc_advantage_pct(tot_i, tot_d))

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    (ax1, ax2), (ax3, ax4) = axes

    x = np.arange(len(groups))
    width = 0.35

    # Cores dinâmicas para ax1 e ax2: Verde para a barra mais rápida, Vermelho para a mais lenta
    colors_tot_i = [COLOR_ICEBERG_WIN if totals["iceberg"][i] < totals["delta_lake"][i] else COLOR_NEUTRAL_1 for i in range(len(groups))]
    colors_tot_d = [COLOR_DELTA_WIN if totals["delta_lake"][i] < totals["iceberg"][i] else COLOR_NEUTRAL_1 for i in range(len(groups))]

    colors_gm_i = [COLOR_ICEBERG_WIN if gmeans["iceberg"][i] < gmeans["delta_lake"][i] else COLOR_NEUTRAL_1 for i in range(len(groups))]
    colors_gm_d = [COLOR_DELTA_WIN if gmeans["delta_lake"][i] < gmeans["iceberg"][i] else COLOR_NEUTRAL_1 for i in range(len(groups))]

    # Painel 1A: Tempo Total Acumulado
    b1_i = ax1.bar(x - width / 2, totals["iceberg"], width, label="Iceberg", color=colors_tot_i, alpha=0.88)
    b1_d = ax1.bar(x + width / 2, totals["delta_lake"], width, label="Delta Lake", color=colors_tot_d, alpha=0.88)
    max_tot = max(max(totals["iceberg"], default=1.0), max(totals["delta_lake"], default=1.0))
    ax1.set_ylim(0, max_tot * 1.25)
    ax1.set_ylabel("Tempo Total Acumulado (s)")
    ax1.set_title("(A) Tempo Total de Execução por Categoria", fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(group_labels)
    ax1.grid(axis="y", alpha=0.3)

    # Legenda semântica customizada para A e B
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLOR_DELTA_WIN, edgecolor="black", label="Delta Lake Vencedor"),
        Patch(facecolor=COLOR_ICEBERG_WIN, edgecolor="black", label="Iceberg Vencedor"),
        Patch(facecolor=COLOR_NEUTRAL_1, edgecolor="black", label="Mais Lento"),
    ]
    ax1.legend(handles=legend_elements, loc="upper left", framealpha=0.9)

    for i in range(len(groups)):
        ti, td = totals["iceberg"][i], totals["delta_lake"][i]
        ax1.annotate(f"{ti:.1f}s", xy=(x[i] - width / 2, ti), xytext=(0, 4),
                     textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
        ax1.annotate(f"{td:.1f}s", xy=(x[i] + width / 2, td), xytext=(0, 4),
                     textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")

    # Painel 1B: Média Geométrica
    ax2.bar(x - width / 2, gmeans["iceberg"], width, label="Iceberg", color=colors_gm_i, alpha=0.88)
    ax2.bar(x + width / 2, gmeans["delta_lake"], width, label="Delta Lake", color=colors_gm_d, alpha=0.88)
    max_gm = max(max(gmeans["iceberg"], default=1.0), max(gmeans["delta_lake"], default=1.0))
    ax2.set_ylim(0, max_gm * 1.25)
    ax2.set_ylabel("Média Geométrica (s)")
    ax2.set_title("(B) Média Geométrica das Consultas (Métrica Padrão TPC)", fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(group_labels)
    ax2.legend(handles=legend_elements, loc="upper left", framealpha=0.9)
    ax2.grid(axis="y", alpha=0.3)

    for i in range(len(groups)):
        gi, gd = gmeans["iceberg"][i], gmeans["delta_lake"][i]
        ax2.annotate(f"{gi:.2f}s", xy=(x[i] - width / 2, gi), xytext=(0, 4),
                     textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
        ax2.annotate(f"{gd:.2f}s", xy=(x[i] + width / 2, gd), xytext=(0, 4),
                     textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")

    # Painel 1C: Speedup Relativo % com Verde para Delta e Vermelho para Iceberg
    colors_sp = [COLOR_DELTA_WIN if s >= 0 else COLOR_ICEBERG_WIN for s in speedups]
    bars_sp = ax3.bar(x, speedups, width=0.45, color=colors_sp, alpha=0.88)
    ax3.axhline(0, color="black", linestyle="--", linewidth=1.1, alpha=0.75)
    ax3.set_ylabel("Vantagem do Delta Lake (% mais rápido)")
    ax3.set_title("(C) Vantagem Relativa por Família e Escala", fontweight="bold")
    ax3.set_xticks(x)
    ax3.set_xticklabels(group_labels)
    ax3.grid(axis="y", alpha=0.3)

    max_sp = max(speedups, default=10.0)
    min_sp = min(speedups, default=0.0)
    top_limit = max(max_sp * 1.35, 12.0)
    bottom_limit = min(min_sp * 1.35, -10.0) if min_sp < 0 else -5.0
    ax3.set_ylim(bottom_limit, top_limit)

    for bar, s in zip(bars_sp, speedups):
        h = bar.get_height()
        pos_y = h + (1.5 if h >= 0 else -3.5)
        ax3.annotate(f"{s:+.1f}%", xy=(bar.get_x() + bar.get_width() / 2, pos_y),
                     ha="center", va="bottom" if h >= 0 else "top", fontweight="bold", fontsize=9.5)

    # Painel 1D: Curva de Escalabilidade Log-Log
    benchmarks = sorted(list({r.get("benchmark", "tpch") for r in baseline_runs}))
    plotted_any = False
    for b in benchmarks:
        b_sfs = sorted(list({r.get("scale_factor") for r in baseline_runs if r.get("benchmark") == b}))
        if len(b_sfs) > 1:
            sf_numeric = [float(sf.lower().replace("sf", "")) for sf in b_sfs]
            ice_means = []
            delta_means = []
            for sf in b_sfs:
                i_t = [r["elapsed_seconds"] for r in baseline_runs if r.get("benchmark") == b and r.get("scale_factor") == sf and r["catalog"] == "iceberg"]
                d_t = [r["elapsed_seconds"] for r in baseline_runs if r.get("benchmark") == b and r.get("scale_factor") == sf and r["catalog"] == "delta_lake"]
                ice_means.append(statistics.mean(i_t) if i_t else 0.0)
                delta_means.append(statistics.mean(d_t) if d_t else 0.0)

            ax4.plot(sf_numeric, ice_means, marker="o", markersize=7, linewidth=2.2, label=f"Iceberg ({b.upper()})", color="#e41a1c", linestyle="-")
            ax4.plot(sf_numeric, delta_means, marker="s", markersize=7, linewidth=2.2, label=f"Delta Lake ({b.upper()})", color="#2ca02c", linestyle="--")
            ax4.set_xscale("log")
            ax4.set_yscale("log")
            ax4.set_xticks(sf_numeric)
            ax4.set_xticklabels([sf.upper() for sf in b_sfs])
            plotted_any = True

    if plotted_any:
        ax4.set_xlabel("Scale Factor (Escala Log)")
        ax4.set_ylabel("Tempo Médio de Consulta (s, Escala Log)")
        ax4.set_title("(D) Curva de Escalabilidade (Log-Log)", fontweight="bold")
        ax4.legend(loc="upper left", framealpha=0.9)
        ax4.grid(True, which="both", alpha=0.3)
    else:
        ax4.text(0.5, 0.5, "Múltiplas escalas necessárias para traçar curva", ha="center", va="center")
        ax4.set_title("(D) Curva de Escalabilidade (Log-Log)", fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_dir / "1_executive_overview.png", dpi=300)
    plt.close()


# ==============================================================================
# FIGURA 2: DETALHAMENTO POR QUERY — BARRAS DIVERGENTES (2_query_divergence.png)
# ==============================================================================
def _plot_query_divergence(runs: list[dict[str, Any]], output_dir: Path) -> None:
    """Gera barras horizontais divergentes centradas em zero (% vantagem Delta sobre Iceberg).
    
    Subpainéis:
    - Coluna Esquerda: TPC-H SF1 e SF10 (22 queries cada)
    - Coluna Direita: TPC-DS SF1 e SF10 (103 queries cada, altura proporcional e ordenada)
    """
    baseline_runs = [r for r in runs if r.get("suite") != "phase2_optimization"]
    benchmarks = ["tpch", "tpcds"]

    # Coleta os dados ordenados por magnitude da diferença
    data_by_case: dict[tuple[str, str], list[tuple[str, float]]] = {}

    for b in benchmarks:
        for sf in ("sf1", "sf10"):
            sub = [r for r in baseline_runs if r.get("benchmark") == b and r.get("scale_factor") == sf]
            queries = sorted(list({r["query"] for r in sub}), key=natural_sort_key)
            diffs: list[tuple[str, float]] = []
            for q in queries:
                iq = [r["elapsed_seconds"] for r in sub if r["catalog"] == "iceberg" and r["query"] == q]
                dq = [r["elapsed_seconds"] for r in sub if r["catalog"] == "delta_lake" and r["query"] == q]
                if iq and dq:
                    avg_i = statistics.mean(iq)
                    avg_d = statistics.mean(dq)
                    pct = calc_advantage_pct(avg_i, avg_d)
                    diffs.append((q, pct))

            # Ordena da menor vantagem (Iceberg vence) à maior vantagem (Delta vence)
            diffs.sort(key=lambda item: item[1])
            if diffs:
                data_by_case[(b, sf)] = diffs

    if not data_by_case:
        return

    # Determinamos a altura da imagem proporcional ao maior conjunto de queries (TPC-DS ~103 queries)
    max_queries_tpcds = max([len(v) for k, v in data_by_case.items() if k[0] == "tpcds"] or [30])
    fig_height = max(24.0, max_queries_tpcds * 0.22)

    # Grid com 4 subplots: 2 linhas x 2 colunas
    # Linha 1: SF1 (TPC-H SF1 e TPC-DS SF1)
    # Linha 2: SF10 (TPC-H SF10 e TPC-DS SF10)
    fig, axes = plt.subplots(2, 2, figsize=(22, fig_height),
                             gridspec_kw={"width_ratios": [1.0, 1.4], "height_ratios": [1, 1]})

    cases = [
        (("tpch", "sf1"), axes[0][0], "TPC-H SF1 (22 Queries)"),
        (("tpcds", "sf1"), axes[0][1], "TPC-DS SF1 (103 Queries)"),
        (("tpch", "sf10"), axes[1][0], "TPC-H SF10 (22 Queries)"),
        (("tpcds", "sf10"), axes[1][1], "TPC-DS SF10 (103 Queries)"),
    ]

    for (b_key, sf_key), ax, title in cases:
        diffs = data_by_case.get((b_key, sf_key), [])
        if not diffs:
            ax.text(0.5, 0.5, f"Sem dados para {title}", ha="center", va="center")
            ax.set_title(title, fontweight="bold")
            continue

        q_labels = [item[0] for item in diffs]
        vals = [item[1] for item in diffs]
        colors = [COLOR_DELTA_WIN if v >= 0 else COLOR_ICEBERG_WIN for v in vals]

        y_pos = np.arange(len(q_labels))
        ax.barh(y_pos, vals, color=colors, alpha=0.88, height=0.72)
        ax.axvline(0, color="black", linestyle="-", linewidth=1.0, alpha=0.8)

        ax.set_yticks(y_pos)
        font_sz = 8 if len(q_labels) > 40 else 8.5
        ax.set_yticklabels(q_labels, fontsize=font_sz)
        ax.set_xlabel("← Iceberg Vence (%) | Delta Lake Vence (%) →", fontsize=9.5)
        ax.set_title(title, fontweight="bold", fontsize=11)
        ax.grid(axis="x", alpha=0.3)

        # Headroom dinâmico no eixo X
        max_abs = max([abs(v) for v in vals] or [10.0])
        limit_x = max(max_abs * 1.15, 25.0)
        ax.set_xlim(-limit_x, limit_x)

        # Anotações de valor numérico nas extremidades mais expressivas
        for idx, val in enumerate(vals):
            # Rotula os 3 maiores e os 3 menores, ou qualquer um com impacto > 30%
            if idx < 3 or idx >= len(vals) - 3 or abs(val) >= 40.0:
                pos_x = val + (limit_x * 0.02 if val >= 0 else -limit_x * 0.02)
                ha = "left" if val >= 0 else "right"
                ax.annotate(f"{val:+.1f}%", xy=(pos_x, idx), va="center", ha=ha,
                            fontsize=7.5, fontweight="bold",
                            color=COLOR_DELTA_WIN if val >= 0 else COLOR_ICEBERG_WIN)

    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=COLOR_DELTA_WIN, edgecolor="black", label="Vantagem Delta Lake (Mais Rápido)"),
        Patch(facecolor=COLOR_ICEBERG_WIN, edgecolor="black", label="Vantagem Apache Iceberg (Mais Rápido)"),
    ]
    fig.legend(handles=legend_elements, loc="upper center", bbox_to_anchor=(0.5, 0.995), ncol=2, framealpha=0.9, fontsize=11)

    plt.tight_layout(rect=[0, 0, 1, 0.985])
    plt.savefig(output_dir / "2_query_divergence.png", dpi=300)
    plt.close()


# ==============================================================================
# FIGURA 3: DISTRIBUIÇÃO EM ESCALA LOG E SCATTER RECOLORIDO (3_distribution_and_scatter.png)
# ==============================================================================
def _plot_distribution_and_scatter(runs: list[dict[str, Any]], output_dir: Path) -> None:
    """Boxplots com escala log no eixo Y + Scatter Plot Delta vs Iceberg recolorido por vencedor."""
    baseline_runs = [r for r in runs if r.get("suite") != "phase2_optimization"]

    fig, (ax_box, ax_scat) = plt.subplots(1, 2, figsize=(18, 7.5))

    # 3A: Boxplots em Escala Logarítmica
    scale_factors = sorted(list({r.get("scale_factor", "sf1") for r in baseline_runs}))
    benchmarks = sorted(list({r.get("benchmark", "tpch") for r in baseline_runs}))

    box_data = []
    labels = []
    box_colors = []

    for sf in scale_factors:
        for b_name in benchmarks:
            sub_i = [r["elapsed_seconds"] for r in baseline_runs
                     if r.get("scale_factor") == sf and r.get("benchmark") == b_name and r["catalog"] == "iceberg"]
            sub_d = [r["elapsed_seconds"] for r in baseline_runs
                     if r.get("scale_factor") == sf and r.get("benchmark") == b_name and r["catalog"] == "delta_lake"]

            if sub_i and sub_d:
                med_i = statistics.median(sub_i)
                med_d = statistics.median(sub_d)

                # Cor dinâmica: Verde para a mediana mais rápida, Vermelho para a mediana mais lenta
                color_i = COLOR_ICEBERG_WIN if med_i < med_d else COLOR_NEUTRAL_1
                color_d = COLOR_DELTA_WIN if med_d < med_i else COLOR_NEUTRAL_1

                box_data.append(sub_i)
                labels.append(f"Iceberg\n{b_name.upper()}-{sf.upper()}")
                box_colors.append(color_i)

                box_data.append(sub_d)
                labels.append(f"Delta\n{b_name.upper()}-{sf.upper()}")
                box_colors.append(color_d)

    if box_data:
        bp = ax_box.boxplot(box_data, tick_labels=labels, patch_artist=True, showmeans=True,
                            meanprops={"marker": "D", "markerfacecolor": "yellow", "markeredgecolor": "black", "markersize": 5})

        for i, patch in enumerate(bp["boxes"]):
            patch.set_facecolor(box_colors[i])
            patch.set_alpha(0.80)

        ax_box.set_yscale("log")
        ax_box.set_ylabel("Tempo de Execução (s, Escala Log)")
        ax_box.set_title("(A) Distribuição dos Tempos de Consulta (Escala Log)", fontweight="bold")
        ax_box.grid(True, which="both", axis="y", alpha=0.3)

        from matplotlib.patches import Patch
        box_legend = [
            Patch(facecolor=COLOR_DELTA_WIN, edgecolor="black", label="Delta Lake (Mediana Mais Rápida)"),
            Patch(facecolor=COLOR_ICEBERG_WIN, edgecolor="black", label="Iceberg (Mediana Mais Rápida)"),
            Patch(facecolor=COLOR_NEUTRAL_1, edgecolor="black", label="Mediana Mais Lenta"),
        ]
        ax_box.legend(handles=box_legend, loc="upper left", framealpha=0.9)

    # 3B: Scatter Plot Delta vs Iceberg com Cores Dinâmicas e Marcadores por SF
    # Verde = ponto onde Delta é mais rápido; Vermelho = ponto onde Iceberg é mais rápido
    # Formas: 'o' para SF1, 's' para SF10
    markers = {"sf1": "o", "sf10": "s", "sf100": "^"}

    point_data: list[tuple[float, float, str, str, str]] = []
    all_d: list[float] = []
    all_i: list[float] = []

    for b in benchmarks:
        for sf in scale_factors:
            sf_runs = [r for r in baseline_runs if r.get("benchmark") == b and r.get("scale_factor") == sf]
            queries = sorted(list({r["query"] for r in sf_runs}), key=natural_sort_key)
            for q in queries:
                iq = [r["elapsed_seconds"] for r in sf_runs if r["catalog"] == "iceberg" and r["query"] == q]
                dq = [r["elapsed_seconds"] for r in sf_runs if r["catalog"] == "delta_lake" and r["query"] == q]
                if iq and dq:
                    ti = statistics.mean(iq)
                    td = statistics.mean(dq)
                    point_data.append((td, ti, q, sf, b))
                    all_d.append(td)
                    all_i.append(ti)

    if point_data:
        max_coord = max(max(all_d), max(all_i)) * 1.15
        ax_scat.plot([0, max_coord], [0, max_coord], color="black", linestyle="--", linewidth=1.3, label="Linha de Paridade (y = x)")

        # Plota cada subgrupo por escala para ter legenda limpa de formas
        for sf in scale_factors:
            sf_pts = [p for p in point_data if p[3] == sf]
            if not sf_pts:
                continue
            xs = [p[0] for p in sf_pts]
            ys = [p[1] for p in sf_pts]
            # Verde se Delta é mais rápido (ys > xs => Iceberg demora mais), Vermelho se Iceberg é mais rápido
            colors = [COLOR_DELTA_WIN if p[0] < p[1] else COLOR_ICEBERG_WIN for p in sf_pts]

            ax_scat.scatter(xs, ys, marker=markers.get(sf, "o"), c=colors, s=55, alpha=0.82,
                            edgecolors="white", linewidths=0.5, label=f"Escala {sf.upper()} (Forma)")

        ax_scat.set_xlim(0, max_coord)
        ax_scat.set_ylim(0, max_coord)
        ax_scat.set_xlabel("Tempo Delta Lake (s)")
        ax_scat.set_ylabel("Tempo Apache Iceberg (s)")
        ax_scat.set_title("(B) Dispersão Cruzada: Delta Lake vs Apache Iceberg", fontweight="bold")
        ax_scat.grid(True, alpha=0.3)

        # Regiões conceituais
        ax_scat.text(max_coord * 0.08, max_coord * 0.90, "▲ Delta Lake Mais Rápido\n(Iceberg mais lento)",
                     color=COLOR_DELTA_WIN, fontsize=9.5, fontweight="bold", fontstyle="italic")
        ax_scat.text(max_coord * 0.58, max_coord * 0.28, "▼ Iceberg Mais Rápido\n(Delta Lake mais lento)",
                     color=COLOR_ICEBERG_WIN, fontsize=9.5, fontweight="bold", fontstyle="italic")

        # Anotações inteligentes nos 5 casos mais extremos
        sorted_diffs = sorted(point_data, key=lambda p: abs(p[0] - p[1]), reverse=True)
        annotated: list[tuple[float, float]] = []
        for td, ti, q, sf, b in sorted_diffs:
            if len(annotated) >= 5:
                break
            # Evita sobreposição física com anotações anteriores
            collision = any(((td - ax[0]) ** 2 + (ti - ax[1]) ** 2) ** 0.5 < (max_coord * 0.12) for ax in annotated)
            if not collision:
                annotated.append((td, ti))
                x_off = -12 if ti > td else 12
                y_off = 10 if ti > td else -14
                ha = "right" if ti > td else "left"
                ax_scat.annotate(
                    f"{q} ({sf.upper()})",
                    xy=(td, ti),
                    xytext=(x_off, y_off),
                    textcoords="offset points",
                    fontsize=8,
                    fontweight="bold",
                    ha=ha,
                    bbox=dict(boxstyle="round,pad=0.25", facecolor="white", alpha=0.92, edgecolor="#666666", linewidth=0.6),
                    arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="#333333", lw=0.7)
                )

        from matplotlib.lines import Line2D
        scat_legend = [
            Line2D([0], [0], color="black", linestyle="--", label="Paridade (y = x)"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_DELTA_WIN, markersize=8, label="Ponto: Delta Vence (Verde)"),
            Line2D([0], [0], marker="o", color="w", markerfacecolor=COLOR_ICEBERG_WIN, markersize=8, label="Ponto: Iceberg Vence (Vermelho)"),
            Line2D([0], [0], marker="o", color="black", markersize=7, linestyle="None", label="SF1 (Círculo)"),
            Line2D([0], [0], marker="s", color="black", markersize=7, linestyle="None", label="SF10 (Quadrado)"),
        ]
        ax_scat.legend(handles=scat_legend, loc="lower right", framealpha=0.92, fontsize=8.5)

    plt.tight_layout()
    plt.savefig(output_dir / "3_distribution_and_scatter.png", dpi=300)
    plt.close()


# ==============================================================================
# FIGURA 4: INFRAESTRUTURA E ESTABILIDADE DAS ITERAÇÕES (4_infrastructure_and_stability.png)
# ==============================================================================
def _plot_infrastructure_and_stability(runs: list[dict[str, Any]], output_dir: Path) -> None:
    """Funde I/O MinIO, Latência de Catálogo, CPU e Coeficiente de Variação (CV) das 3 iterações."""
    catalogs = ["iceberg", "delta_lake"]
    scale_factors = sorted(list({r.get("scale_factor", "sf1") for r in runs}))

    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    (ax_io, ax_plan), (ax_cpu, ax_cv) = axes

    x = np.arange(len(scale_factors))
    width = 0.35

    # 4A: MinIO Storage I/O (MB Lidos do MinIO - Worker 1)
    io_mb: dict[str, list[float]] = {cat: [] for cat in catalogs}
    for sf in scale_factors:
        sf_runs = [r for r in runs if r.get("scale_factor", "sf1") == sf]
        for cat in catalogs:
            bytes_total = sum(r.get("physical_input_bytes") or 0 for r in sf_runs if r["catalog"] == cat)
            io_mb[cat].append(bytes_total / (1024 * 1024))

    ax_io.bar(x - width / 2, io_mb["iceberg"], width, label="Iceberg", color=COLOR_NEUTRAL_1, alpha=0.88)
    ax_io.bar(x + width / 2, io_mb["delta_lake"], width, label="Delta Lake", color=COLOR_NEUTRAL_2, alpha=0.88)
    max_io = max(max(io_mb["iceberg"], default=1.0), max(io_mb["delta_lake"], default=1.0))
    ax_io.set_ylim(0, max_io * 1.25)
    ax_io.set_ylabel("MB Lidos do MinIO")
    ax_io.set_title("(A) Tráfego de Storage I/O no MinIO (Worker 1)", fontweight="bold")
    ax_io.set_xticks(x)
    ax_io.set_xticklabels([sf.upper() for sf in scale_factors])
    ax_io.legend(loc="upper left", framealpha=0.9)
    ax_io.grid(axis="y", alpha=0.3)

    for i, sf in enumerate(scale_factors):
        ax_io.annotate(f"{io_mb['iceberg'][i]:.0f} MB", xy=(x[i] - width / 2, io_mb["iceberg"][i]),
                       xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
        ax_io.annotate(f"{io_mb['delta_lake'][i]:.0f} MB", xy=(x[i] + width / 2, io_mb["delta_lake"][i]),
                       xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")

    # 4B: Latência do Catálogo (Planning Time em ms - Worker 5)
    plan_ms: dict[str, list[float]] = {cat: [] for cat in catalogs}
    for sf in scale_factors:
        sf_runs = [r for r in runs if r.get("scale_factor", "sf1") == sf]
        for cat in catalogs:
            times = [r.get("planning_time_ms") or 0.0 for r in sf_runs if r["catalog"] == cat]
            plan_ms[cat].append(statistics.mean(times) if times else 0.0)

    ax_plan.bar(x - width / 2, plan_ms["iceberg"], width, label="Iceberg (Postgres JDBC)", color=COLOR_NEUTRAL_1, alpha=0.88)
    ax_plan.bar(x + width / 2, plan_ms["delta_lake"], width, label="Delta Lake (Hive Metastore)", color=COLOR_NEUTRAL_2, alpha=0.88)
    max_plan = max(max(plan_ms["iceberg"], default=1.0), max(plan_ms["delta_lake"], default=1.0))
    ax_plan.set_ylim(0, max_plan * 1.25)
    ax_plan.set_ylabel("Planning Time Médio (ms)")
    ax_plan.set_title("(B) Latência de Resolução de Metadados no Catálogo (Worker 5)", fontweight="bold")
    ax_plan.set_xticks(x)
    ax_plan.set_xticklabels([sf.upper() for sf in scale_factors])
    ax_plan.legend(loc="upper left", framealpha=0.9)
    ax_plan.grid(axis="y", alpha=0.3)

    for i, sf in enumerate(scale_factors):
        ax_plan.annotate(f"{plan_ms['iceberg'][i]:.1f}ms", xy=(x[i] - width / 2, plan_ms["iceberg"][i]),
                         xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
        ax_plan.annotate(f"{plan_ms['delta_lake'][i]:.1f}ms", xy=(x[i] + width / 2, plan_ms["delta_lake"][i]),
                         xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")

    # 4C: CPU Time Acumulado nos Nós de Computação (Workers 2, 3 e 4)
    cpu_s: dict[str, list[float]] = {cat: [] for cat in catalogs}
    for sf in scale_factors:
        sf_runs = [r for r in runs if r.get("scale_factor", "sf1") == sf]
        for cat in catalogs:
            c_times = [(r.get("cpu_time_ms") or 0.0) / 1000.0 for r in sf_runs if r["catalog"] == cat]
            cpu_s[cat].append(sum(c_times))

    ax_cpu.bar(x - width / 2, cpu_s["iceberg"], width, label="Iceberg", color=COLOR_NEUTRAL_1, alpha=0.88)
    ax_cpu.bar(x + width / 2, cpu_s["delta_lake"], width, label="Delta Lake", color=COLOR_NEUTRAL_2, alpha=0.88)
    max_cpu = max(max(cpu_s["iceberg"], default=1.0), max(cpu_s["delta_lake"], default=1.0))
    ax_cpu.set_ylim(0, max_cpu * 1.25)
    ax_cpu.set_ylabel("CPU Time Acumulado (s)")
    ax_cpu.set_title("(C) CPU Time nos Nós de Computação (Workers 2-4)", fontweight="bold")
    ax_cpu.set_xticks(x)
    ax_cpu.set_xticklabels([sf.upper() for sf in scale_factors])
    ax_cpu.legend(loc="upper left", framealpha=0.9)
    ax_cpu.grid(axis="y", alpha=0.3)

    for i, sf in enumerate(scale_factors):
        ax_cpu.annotate(f"{cpu_s['iceberg'][i]:.0f}s", xy=(x[i] - width / 2, cpu_s["iceberg"][i]),
                        xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")
        ax_cpu.annotate(f"{cpu_s['delta_lake'][i]:.0f}s", xy=(x[i] + width / 2, cpu_s["delta_lake"][i]),
                        xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8.5, fontweight="bold")

    # 4D: Estabilidade / Ruído de Infraestrutura (Coeficiente de Variação - CV %)
    # Calcula CV = (std / mean) * 100 para cada query e catálogo nas 3 iterações
    # Identifica as queries com maior instabilidade (maior CV)
    cv_records: list[dict[str, Any]] = []
    baseline_runs = [r for r in runs if r.get("suite") != "phase2_optimization"]
    all_queries = sorted(list({r["query"] for r in baseline_runs}), key=natural_sort_key)

    for q in all_queries:
        for sf in scale_factors:
            for cat in catalogs:
                times = [r["elapsed_seconds"] for r in baseline_runs
                         if r.get("scale_factor") == sf and r["query"] == q and r["catalog"] == cat]
                if len(times) >= 2:
                    mean_val = statistics.mean(times)
                    std_val = statistics.stdev(times)
                    cv_val = (std_val / mean_val * 100.0) if mean_val > 0 else 0.0
                    cv_records.append({
                        "query": q,
                        "scale_factor": sf,
                        "catalog": cat,
                        "cv": cv_val,
                        "mean": mean_val,
                        "std": std_val,
                    })

    if cv_records:
        # Pega as 10 queries com maior CV absoluto (maior ruído temporal)
        top_unstable = sorted(cv_records, key=lambda x: x["cv"], reverse=True)[:12]
        labels_cv = [f"{r['query']}\n({r['catalog'][:3].upper()}-{r['scale_factor'].upper()})" for r in top_unstable]
        vals_cv = [r["cv"] for r in top_unstable]
        colors_cv = [COLOR_ICEBERG_WIN if r["catalog"] == "iceberg" else COLOR_DELTA_WIN for r in top_unstable]

        x_cv = np.arange(len(top_unstable))
        bars_cv = ax_cv.bar(x_cv, vals_cv, color=colors_cv, alpha=0.88, width=0.55)
        ax_cv.set_ylabel("Coeficiente de Variação (%)")
        ax_cv.set_title("(D) Top 12 Consultas com Maior Instabilidade Temporal (CV %)", fontweight="bold")
        ax_cv.set_xticks(x_cv)
        ax_cv.set_xticklabels(labels_cv, fontsize=7.5)
        ax_cv.grid(axis="y", alpha=0.3)

        max_cv = max(vals_cv, default=10.0)
        ax_cv.set_ylim(0, max_cv * 1.25)

        for bar, val in zip(bars_cv, vals_cv):
            ax_cv.annotate(f"{val:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                           xytext=(0, 4), textcoords="offset points", ha="center", fontsize=8, fontweight="bold")

        from matplotlib.patches import Patch
        cv_legend = [
            Patch(facecolor=COLOR_ICEBERG_WIN, edgecolor="black", label="Iceberg Instável"),
            Patch(facecolor=COLOR_DELTA_WIN, edgecolor="black", label="Delta Lake Instável"),
        ]
        ax_cv.legend(handles=cv_legend, loc="upper right", framealpha=0.9)
    else:
        ax_cv.text(0.5, 0.5, "Necessário >= 2 iterações por query para calcular CV", ha="center", va="center")
        ax_cv.set_title("(D) Coeficiente de Variação das Iterações (CV %)", fontweight="bold")

    plt.tight_layout()
    plt.savefig(output_dir / "4_infrastructure_and_stability.png", dpi=300)
    plt.close()


# ==============================================================================
# RENDERIZADOR MARKDOWN MASTER
# ==============================================================================
def _render_master_markdown(runs: list[dict[str, Any]], plots_dir: Path, report_path: Path) -> None:
    scale_factors = sorted(list({r.get("scale_factor", "sf1") for r in runs}))
    benchmarks = sorted(list({r.get("benchmark", "tpch") for r in runs}))

    baseline_runs = [r for r in runs if r.get("suite") != "phase2_optimization"]
    total_iceberg = sum(r["elapsed_seconds"] for r in baseline_runs if r["catalog"] == "iceberg")
    total_delta = sum(r["elapsed_seconds"] for r in baseline_runs if r["catalog"] == "delta_lake")
    overall_speedup = (total_iceberg / total_delta) if total_delta > 0 else 1.0
    overall_winner = "Delta Lake" if total_delta < total_iceberg else "Apache Iceberg"
    pct_diff = abs(total_iceberg - total_delta) / max(total_iceberg, total_delta) * 100 if max(total_iceberg, total_delta) > 0 else 0

    lines = [
        "# Relatório Consolidado de Desempenho: Apache Iceberg vs Delta Lake",
        "",
        f"**Data da Execução:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        "**Motor de Consulta:** Trino 483  ",
        "**Armazenamento de Objetos:** MinIO S3 (Worker 1 Dedicado)  ",
        "**Catálogos de Metadados:** PostgreSQL (Iceberg JDBC) & Hive Metastore (Delta Lake) (Worker 5 Dedicado)  ",
        "**Infraestrutura:** Cluster Kubernetes (K3s) em 6 Nós físicos dedicados na Magalu Cloud  ",
        "",
        "---",
        "",
        "## 📑 Sumário Executivo",
        "",
        f"- **Vencedor Geral:** **{overall_winner}** ({pct_diff:.1f}% mais rápido em tempo total acumulado)",
        f"- **Tempo Total Iceberg:** {total_iceberg:.2f}s",
        f"- **Tempo Total Delta Lake:** {total_delta:.2f}s",
        f"- **Speedup Geral:** {overall_speedup:.2f}x",
        f"- **Scale Factors Avaliados:** {', '.join(sf.upper() for sf in scale_factors)}",
        f"- **Famílias de Benchmark:** {', '.join(b.upper() for b in benchmarks)}",
        f"- **Total de Execuções Analisadas:** {len(runs):,} iterações registradas",
        "",
        "---",
        "",
        "## 1. Visão Geral Executiva e Escalabilidade",
        "",
        "Painel consolidando Tempo Total Acumulado, Média Geométrica das consultas (métrica padrão TPC imune a distorções por outliers), Speedup Relativo (%) e Curva de Escalabilidade (Log-Log) entre SF1 e SF10.",
        "",
        f"![Visão Geral Executiva]({os.path.relpath(plots_dir / '1_executive_overview.png', report_path.parent)})",
        "",
        "---",
        "",
        "## 2. Detalhamento Consulta a Consulta (Barras Divergentes Ordenadas)",
        "",
        "Barras horizontais divergentes centradas em zero, ordenadas pela magnitude do ganho percentual. Barras **verdes para a direita** indicam vitória do Delta Lake; barras **vermelhas para a esquerda** indicam vitória do Apache Iceberg.",
        "",
        f"![Detalhamento por Consulta]({os.path.relpath(plots_dir / '2_query_divergence.png', report_path.parent)})",
        "",
        "---",
        "",
        "## 3. Distribuição Estatística e Dispersão Cruzada",
        "",
        "O painel esquerdo apresenta diagramas de caixa (*boxplots*) com **escala logarítmica no eixo Y**, permitindo a comparação uniforme da dispersão de SF1 e SF10 sem esmagamento das caixas. O painel direito apresenta a dispersão cruzada com linha de paridade $y = x$, colorindo em **verde** as consultas onde o Delta Lake foi mais rápido e em **vermelho** onde o Iceberg foi mais rápido, distinguindo as escalas por marcadores geométricos.",
        "",
        f"![Distribuição e Dispersão]({os.path.relpath(plots_dir / '3_distribution_and_scatter.png', report_path.parent)})",
        "",
        "---",
        "",
        "## 4. Métricas de Infraestrutura e Estabilidade Temporal (Variância das Iterações)",
        "",
        "Métricas físicas dos nós isolados na Magalu Cloud: Volume de I/O lido do MinIO (Worker 1), Latência de Catálogo (Worker 5) e CPU Time nos nós de computação (Workers 2-4). O subpainel inferior introduz a **análise de variabilidade temporal via Coeficiente de Variação ($CV = \\frac{\\sigma}{\\mu} \\times 100\\%$)** calculado entre as 3 repetições de cada consulta, destacando as consultas com maior ruído de rede/cache.",
        "",
        f"![Infraestrutura e Estabilidade]({os.path.relpath(plots_dir / '4_infrastructure_and_stability.png', report_path.parent)})",
        "",
        "---",
        "",
        "## 📊 Tabelas Estatísticas Detalhadas",
        "",
    ]

    for sf in scale_factors:
        lines.append(f"### Tabela de Métricas — {sf.upper()}")
        lines.append("")
        lines.append("| Benchmark | Query | Iceberg Média (s) | Delta Média (s) | Speedup | CV Iceberg (%) | CV Delta (%) | Planning Iceberg (ms) | Planning Delta (ms) | MinIO I/O Iceberg (MB) | MinIO I/O Delta (MB) |")
        lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

        sf_runs = [r for r in baseline_runs if r.get("scale_factor", "sf1") == sf]
        queries = sorted(list({r["query"] for r in sf_runs}), key=natural_sort_key)

        for q in queries:
            iq = [r for r in sf_runs if r["catalog"] == "iceberg" and r["query"] == q]
            dq = [r for r in sf_runs if r["catalog"] == "delta_lake" and r["query"] == q]

            ti_list = [r["elapsed_seconds"] for r in iq]
            td_list = [r["elapsed_seconds"] for r in dq]

            avg_i = statistics.mean(ti_list) if ti_list else 0.0
            avg_d = statistics.mean(td_list) if td_list else 0.0
            sp = avg_i / avg_d if avg_d > 0 else 1.0

            cv_i = (statistics.stdev(ti_list) / avg_i * 100.0) if len(ti_list) >= 2 and avg_i > 0 else 0.0
            cv_d = (statistics.stdev(td_list) / avg_d * 100.0) if len(td_list) >= 2 and avg_d > 0 else 0.0

            pi_ms = statistics.mean([r.get("planning_time_ms") or 0.0 for r in iq]) if iq else 0.0
            pd_ms = statistics.mean([r.get("planning_time_ms") or 0.0 for r in dq]) if dq else 0.0

            bio_i = sum(r.get("physical_input_bytes") or 0 for r in iq) / (len(iq) * 1024 * 1024) if iq else 0.0
            bio_d = sum(r.get("physical_input_bytes") or 0 for r in dq) / (len(dq) * 1024 * 1024) if dq else 0.0

            b_type = iq[0].get("benchmark", "tpch").upper() if iq else "TPC-H"
            lines.append(f"| {b_type} | {q} | {avg_i:.2f} | {avg_d:.2f} | {sp:.2f}x | {cv_i:.1f}% | {cv_d:.1f}% | {pi_ms:.1f} | {pd_ms:.1f} | {bio_i:.1f} | {bio_d:.1f} |")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
