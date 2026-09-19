#!/usr/bin/env python3
"""Ponto de entrada unificado para execução dos benchmarks do Lakehouse.

Suporta benchmarks TPC-H (Fase 1 Baseline e Fase 2 Otimizações) e TPC-DS com múltiplos
Scale Factors (SF1 e SF10 por padrão; SF100 sob demanda):

    # Execução padrão (TPC-H Fase 1 + Fase 2 + TPC-DS em SF1 e SF10, 3 iterações):
    python run_benchmark.py

    # Execução específica apenas TPC-H em SF1:
    python run_benchmark.py --benchmark tpch --scale-factor sf1

    # Execução apenas TPC-DS em SF10:
    python run_benchmark.py --benchmark tpcds --scale-factor sf10

    # Executar grande escala SF100 explicitamente:
    python run_benchmark.py --scale-factor sf100

    # Regerar apenas os relatórios consolidados e os 6 grupos de gráficos a partir de execuções existentes:
    python run_benchmark.py --report-only
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

# Garante que a raiz do projeto esteja no sys.path
_repo_root = Path(__file__).resolve().parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

# Se executado com python do sistema fora do virtualenv, relança com ./env/bin/python se existir
_venv_python = _repo_root / "env" / "bin" / "python"
if _venv_python.exists() and sys.executable != str(_venv_python):
    import os
    os.execv(str(_venv_python), [str(_venv_python)] + sys.argv)

from benchmark.common.config import TrinoSettings
from benchmark.common.results import load_json, write_csv, write_json
from benchmark.common.reporting_consolidated import generate_consolidated_report
from benchmark.phase1_baseline.run_benchmark import run_phase1
from benchmark.phase2_optimization.run_benchmark import run_phase2
from benchmark.tpcds.run_benchmark import run_tpcds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Suíte Unificada de Benchmarks Lakehouse (Iceberg vs Delta Lake)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--benchmark",
        choices=["all", "tpch", "tpcds"],
        default="all",
        help="Família de benchmark: 'all' (ambos TPC-H e TPC-DS), 'tpch' ou 'tpcds'",
    )
    parser.add_argument(
        "--scale-factor",
        "--sf",
        dest="scale_factor",
        type=str,
        default=None,
        help="Scale factor único a executar (ex: sf1, sf10, sf100). Sobrescreve --scale-factors.",
    )
    parser.add_argument(
        "--scale-factors",
        type=str,
        default=None,
        help="Lista de scale factors separados por vírgula (ex: 'sf1,sf10'). Padrão se não informado: 'sf1,sf10'.",
    )
    parser.add_argument(
        "--suite",
        choices=["all", "phase1", "phase2"],
        default="all",
        help="Qual fase do TPC-H executar ('all' executa Fase 1 Baseline e Fase 2 Otimizações)",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Força provisionamento e carga de dados antes dos testes (auto-detecção já é ativa)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Descarta e recria tabelas/schemas existentes durante o setup (requer --setup)",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Quantidade de repetições por consulta (padrão: 3 para rigor estatístico)",
    )
    parser.add_argument(
        "--skip-explain",
        action="store_true",
        help="Ignora a etapa de EXPLAIN ANALYZE na Fase 2",
    )
    parser.add_argument(
        "--continue-on-setup-errors",
        action="store_true",
        help="Continua a execução mesmo se houver falhas pontuais no setup",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Apenas consolida os dados de runs salvos em disco e regera os 6 gráficos e o benchmark_report.md",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmark_results"),
        help="Diretório de saída unificado para todos os artefatos, relatórios e gráficos",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Caminho do relatório consolidado Markdown mestre (padrão: <output-dir>/benchmark_report.md)",
    )
    parser.add_argument(
        "--output-dir-phase1",
        type=Path,
        default=None,
        help="Diretório de saída customizado para artefatos e gráficos do TPC-H Fase 1",
    )
    parser.add_argument(
        "--output-dir-phase2",
        type=Path,
        default=None,
        help="Diretório de saída customizado para artefatos e planos do TPC-H Fase 2",
    )
    parser.add_argument(
        "--output-dir-tpcds",
        type=Path,
        default=None,
        help="Diretório de saída customizado para artefatos e gráficos do TPC-DS",
    )
    parser.add_argument(
        "--report-path-tpcds",
        type=Path,
        default=None,
        help="Caminho do relatório individual Markdown do TPC-DS",
    )
    parsed = parser.parse_args()
    if parsed.report_path is None:
        parsed.report_path = parsed.output_dir / "benchmark_report.md"
    return parsed


def run_for_scale_factor(
    args: argparse.Namespace,
    sf: str,
    all_runs: list[dict[str, Any]],
) -> dict[str, int]:
    exit_codes: dict[str, int] = {}
    normalized_sf = sf.lower() if sf.startswith("sf") or sf == "tiny" else f"sf{sf.lower()}"

    p1_out = args.output_dir_phase1 or (args.output_dir / f"tpch_{normalized_sf}")
    p2_out = args.output_dir_phase2 or (args.output_dir / f"phase2_{normalized_sf}")
    ds_out = args.output_dir_tpcds or (args.output_dir / f"tpcds_{normalized_sf}")
    ds_rep = args.report_path_tpcds or (ds_out / f"benchmark_report_tpcds_{normalized_sf}.md")

    settings_p1 = TrinoSettings.from_environment(
        output_dir=p1_out,
        iterations=args.iterations,
        scale_factor=normalized_sf,
        benchmark_type="tpch",
    )
    settings_p2 = TrinoSettings.from_environment(
        output_dir=p2_out,
        iterations=args.iterations,
        scale_factor=normalized_sf,
        benchmark_type="tpch",
    )
    settings_ds = TrinoSettings.from_environment(
        output_dir=ds_out,
        iterations=args.iterations,
        scale_factor=normalized_sf,
        benchmark_type="tpcds",
    )

    print("\n" + "=" * 76)
    print(f" EXECUTANDO BENCHMARKS LAKEHOUSE [SCALE FACTOR: {normalized_sf.upper()}]")
    print("=" * 76)
    print(f" Coordinator Trino : {settings_p1.host}:{settings_p1.port} (Usuário: {settings_p1.user})")
    print(f" Família Selecionada: {args.benchmark.upper()}")
    print(f" Fases TPC-H        : {args.suite.upper()}")
    print(f" Executar Setup     : {'SIM' if args.setup else 'NÃO'}" + (" (REPLACE)" if args.replace else ""))
    print(f" Iterações/query    : {settings_p1.iterations}")
    print("=" * 76 + "\n")

    # 1. TPC-H Fase 1 (Baseline)
    if args.benchmark in ("all", "tpch") and args.suite in ("all", "phase1"):
        p1_rep = p1_out / f"benchmark_report_{normalized_sf}.md"
        code_p1 = run_phase1(
            settings=settings_p1,
            setup=args.setup,
            replace=args.replace,
            continue_on_setup_errors=args.continue_on_setup_errors,
            output_dir=p1_out,
            report_path=p1_rep,
            runs_collector=all_runs,
        )
        exit_codes[f"TPC-H Fase 1 ({normalized_sf.upper()})"] = code_p1

    # 2. TPC-H Fase 2 (Otimizações & Data Skipping)
    if args.benchmark in ("all", "tpch") and args.suite in ("all", "phase2"):
        if args.suite == "all":
            print("\n" + "-" * 76 + "\n")
        code_p2 = run_phase2(
            settings=settings_p2,
            setup=args.setup,
            replace=args.replace,
            continue_on_setup_errors=args.continue_on_setup_errors,
            output_dir=p2_out,
            skip_explain=args.skip_explain,
            runs_collector=all_runs,
        )
        exit_codes[f"TPC-H Fase 2 ({normalized_sf.upper()})"] = code_p2

    # 3. TPC-DS (Decision Support)
    if args.benchmark in ("all", "tpcds"):
        print("\n" + "-" * 76 + "\n")
        ds_rep = ds_out / f"benchmark_report_tpcds_{normalized_sf}.md"
        code_ds = run_tpcds(
            settings=settings_ds,
            setup=args.setup,
            replace=args.replace,
            continue_on_setup_errors=args.continue_on_setup_errors,
            output_dir=ds_out,
            report_path=ds_rep,
            runs_collector=all_runs,
        )
        exit_codes[f"TPC-DS ({normalized_sf.upper()})"] = code_ds

    return exit_codes


def collect_saved_runs(base_dir: Path) -> list[dict[str, Any]]:
    """Carrega runs previamente persistidos em disco caso estejam disponíveis."""
    all_runs: list[dict[str, Any]] = []
    seen: set[str] = set()

    # 1. Busca recursiva por todos os runs*.json dentro de base_dir (ex: benchmark_results/)
    if base_dir.exists():
        for sp in sorted(base_dir.rglob("runs*.json")):
            if sp.name == "runs_all.json":
                continue
            entries = load_json(sp)
            if isinstance(entries, list):
                for e in entries:
                    key = f"{e.get('benchmark')}_{e.get('scale_factor')}_{e.get('suite')}_{e.get('catalog')}_{e.get('query')}_{e.get('iteration')}"
                    if key not in seen:
                        seen.add(key)
                        all_runs.append(e)

    # 2. Se houver runs_all.json consolidado em base_dir, agrega eventuais execuções presentes nele
    candidate_all = base_dir / "runs_all.json"
    if candidate_all.exists():
        entries = load_json(candidate_all)
        if isinstance(entries, list):
            for e in entries:
                key = f"{e.get('benchmark')}_{e.get('scale_factor')}_{e.get('suite')}_{e.get('catalog')}_{e.get('query')}_{e.get('iteration')}"
                if key not in seen:
                    seen.add(key)
                    all_runs.append(e)

    return all_runs


def main() -> int:
    args = parse_args()

    if args.replace and not args.setup:
        print("[ERRO] O argumento --replace requer obrigatoriamente a flag --setup.", file=sys.stderr)
        return 1

    # Modo somente relatório
    if args.report_only:
        print("\n" + "=" * 76)
        print(" CONSOLIDAÇÃO DE RELATÓRIO E GRÁFICOS (MODO --report-only)")
        print("=" * 76)
        all_runs = collect_saved_runs(args.output_dir)
        if not all_runs:
            print(f"[ERRO] Nenhum arquivo de execuções encontrado em {args.output_dir} ou nos diretórios de suites.")
            return 1

        print(f"[INFO] Total de {len(all_runs)} execuções carregadas do disco.")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_csv(args.output_dir / "runs_all.csv", all_runs)
        write_json(args.output_dir / "runs_all.json", all_runs)

        # Gráficos separados: 4 apenas Baseline e 4 apenas Phase2
        baseline_out = args.output_dir / "baseline"
        phase2_out = args.output_dir / "phase2"
        baseline_report = baseline_out / "benchmark_report_baseline.md"
        phase2_report = phase2_out / "benchmark_report_phase2.md"

        generate_consolidated_report(all_runs, baseline_out, baseline_report, suite_filter="baseline")
        generate_consolidated_report(all_runs, phase2_out, phase2_report, suite_filter="phase2")

        print(f"\n[SUCESSO] Relatório baseline gerado em: {baseline_report}")
        print(f"[SUCESSO] Gráficos baseline salvos em:  {baseline_out}/")
        print(f"[SUCESSO] Relatório phase2 gerado em:   {phase2_report}")
        print(f"[SUCESSO] Gráficos phase2 salvos em:    {phase2_out}/")
        print("=" * 76 + "\n")
        return 0

    # Determinação dos Scale Factors: Padrão é SF1 e SF10. SF100 apenas se explícito.
    if args.scale_factor:
        scale_factors = [args.scale_factor.strip()]
    elif args.scale_factors:
        scale_factors = [s.strip() for s in args.scale_factors.split(",") if s.strip()]
    else:
        scale_factors = ["sf1", "sf10"]

    all_exit_codes: dict[str, int] = {}
    all_runs: list[dict[str, Any]] = []

    for sf in scale_factors:
        codes = run_for_scale_factor(args, sf, all_runs)
        all_exit_codes.update(codes)

    # Persistência e geração consolidada master
    if all_runs:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_csv(args.output_dir / "runs_all.csv", all_runs)
        write_json(args.output_dir / "runs_all.json", all_runs)

        # Gráficos separados: 4 apenas Baseline e 4 apenas Phase2
        baseline_out = args.output_dir / "baseline"
        phase2_out = args.output_dir / "phase2"
        generate_consolidated_report(
            all_runs,
            baseline_out,
            baseline_out / "benchmark_report_baseline.md",
            suite_filter="baseline",
        )
        generate_consolidated_report(
            all_runs,
            phase2_out,
            phase2_out / "benchmark_report_phase2.md",
            suite_filter="phase2",
        )

    # Resumo final consolidado
    print("\n" + "=" * 76)
    print(" RESUMO DA EXECUÇÃO")
    print("=" * 76)
    all_success = True
    for suite_name, code in all_exit_codes.items():
        status = "SUCESSO" if code == 0 else f"FALHA (código {code})"
        if code != 0:
            all_success = False
        print(f" - {suite_name:30}: {status}")

    if all_success:
        print("\n Artefatos gerados:")
        print(f"   * Figuras Baseline (4 gráficos) : {args.output_dir / 'baseline'}/")
        print(f"   * Figuras Phase2   (4 gráficos) : {args.output_dir / 'phase2'}/")
        print(f"   * Dados Brutos Consolidados     : {args.output_dir / 'runs_all.json'}")
        if any("TPC-H Fase 1" in k for k in all_exit_codes):
            print(f"   * Gráficos Baseline TPC-H       : {args.output_dir_phase1}/")
        if any("TPC-H Fase 2" in k for k in all_exit_codes):
            print(f"   * Sumário Otimizações TPC-H     : {args.output_dir_phase2 / 'summary.md'}")
            print(f"   * Planos EXPLAIN ANALYZE        : {args.output_dir_phase2 / 'plans'}/")
        if any("TPC-DS" in k for k in all_exit_codes):
            print(f"   * Relatórios Individuais TPC-DS : {args.report_path_tpcds}")
            print(f"   * Gráficos Individuais TPC-DS   : {args.output_dir_tpcds}/")
        print("=" * 76 + "\n")
        return 0
    else:
        print("\n[ERRO] Pelo menos uma das etapas selecionadas apresentou falha.")
        print("=" * 76 + "\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
