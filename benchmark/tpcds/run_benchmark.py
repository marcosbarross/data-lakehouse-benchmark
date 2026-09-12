"""Executor da suíte TPC-DS (Decision Support) - Iceberg vs Delta Lake."""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Garante que a raiz do repositório esteja no sys.path
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from benchmark.common.config import TrinoSettings
from benchmark.common.results import write_csv, write_json
from benchmark.common.trino_client import TrinoClient
from benchmark.tpcds.queries import TPCDS_QUERIES
from benchmark.tpcds.reporting import generate_markdown_report, generate_plots
from benchmark.tpcds.setup import prepare

CATALOGS = ["iceberg", "delta_lake"]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark TPC-DS (Decision Support) — Iceberg vs Delta Lake")
    parser.add_argument("--setup", action="store_true", help="Cria tabelas do TPC-DS nos catálogos Iceberg e Delta Lake")
    parser.add_argument("--replace", action="store_true", help="Remove tabelas existentes antes do setup (requer --setup)")
    parser.add_argument("--scale-factor", type=str, default="sf1", help="Scale factor (ex: sf1, sf10, sf100)")
    parser.add_argument("--iterations", type=int, default=None, help="Número de iterações por consulta")
    parser.add_argument("--output-dir", type=Path, default=None, help="Diretório de saída")
    parser.add_argument("--report-path", type=Path, default=None, help="Caminho do relatório")
    parser.add_argument("--continue-on-setup-errors", action="store_true", help="Continua mesmo se houver erros no setup")
    return parser.parse_args()


def run_tpcds(
    settings: TrinoSettings,
    setup: bool = False,
    replace: bool = False,
    continue_on_setup_errors: bool = False,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    schema: str | None = None,
    runs_collector: list[dict[str, Any]] | None = None,
) -> int:
    """Executa a suíte de benchmark TPC-DS."""
    target_schema = schema or settings.target_schema()
    normalized_sf = settings.scale_factor.lower() if settings.scale_factor.startswith("sf") else f"sf{settings.scale_factor.lower()}"
    plots_dir = output_dir or Path(f"benchmark_results/tpcds_{normalized_sf}")
    report_file = report_path or (plots_dir / f"benchmark_report_tpcds_{normalized_sf}.md")
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"BENCHMARK TPC-DS {settings.scale_factor.upper()}: DECISION SUPPORT (ICEBERG vs DELTA LAKE)")
    print("=" * 70)

    client = TrinoClient(settings)

    # Verificação se todas as tabelas já existem caso --setup não seja passado
    if not setup:
        from benchmark.tpcds.queries import TPCDS_TABLES
        missing: list[str] = []
        for cat in CATALOGS:
            for probe_table in TPCDS_TABLES:
                chk = client.execute(f"SELECT 1 FROM {cat}.{target_schema}.{probe_table} LIMIT 1", catalog=cat)
                if chk.error:
                    missing.append(f"{cat}.{target_schema}.{probe_table}")
                    break
        if missing:
            print(f"\n[AVISO] Tabelas do TPC-DS ({target_schema}) pendentes: {missing[:2]}")
            print(f"[AUTO-SETUP] Executando o provisionamento dos dados automaticamente...")
            setup = True

    if setup:
        errors = prepare(settings, replace=replace, schema=target_schema)
        if errors:
            write_json(plots_dir / "setup_errors.json", errors)
            print(f"[AVISO] Setup TPC-DS finalizado com {len(errors)} erro(s).")
            if not continue_on_setup_errors:
                print("[ERRO] Abortando benchmark devido a falhas no setup.")
                return 1

    results: dict[str, Any] = {catalog: {} for catalog in CATALOGS}
    raw_runs: list[dict[str, Any]] = []

    for catalog in CATALOGS:
        print(f"\n[BENCHMARK TPC-DS] Executando consultas no catálogo '{catalog}'...")
        for query_name, query_template in TPCDS_QUERIES.items():
            sql = query_template.format(catalog=catalog, schema=target_schema)
            print(f"  [EXEC] {query_name} em {catalog}...")
            times: list[float] = []

            for iteration in range(1, settings.iterations + 1):
                res = client.execute(sql, catalog=catalog)
                raw_runs.append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "catalog": catalog,
                    "suite": "tpcds",
                    "benchmark": "tpcds",
                    "scale_factor": settings.scale_factor,
                    "query": query_name,
                    "iteration": iteration,
                    "elapsed_seconds": round(res.elapsed_seconds, 6),
                    "planning_time_ms": res.planning_time_ms,
                    "execution_time_ms": res.execution_time_ms,
                    "cpu_time_ms": res.cpu_time_ms,
                    "physical_input_bytes": res.physical_input_bytes,
                    "processed_bytes": res.processed_bytes,
                    "peak_memory_bytes": res.peak_memory_bytes,
                    "splits_count": res.splits_count,
                    "row_count": res.row_count,
                    "error": res.error,
                })

                if res.error:
                    print(f"    Iteracao {iteration}: ERRO - {res.error}")
                else:
                    times.append(res.elapsed_seconds)
                    print(f"    Iteracao {iteration}: {res.elapsed_seconds:.3f}s ({res.row_count} linhas)")

            if times:
                results[catalog][query_name] = {
                    "times": times,
                    "avg_time": statistics.mean(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "std_dev": statistics.stdev(times) if len(times) > 1 else 0.0,
                }
                print(f"    [OK] Média: {results[catalog][query_name]['avg_time']:.3f}s")

    # Gravar execuções brutas
    write_csv(plots_dir / "runs.csv", raw_runs)
    write_json(plots_dir / "runs.json", raw_runs)

    if runs_collector is not None:
        runs_collector.extend(raw_runs)

    # Gerar gráficos e relatório
    generate_plots(results, plots_dir, scale_factor=settings.scale_factor)
    generate_markdown_report(results, settings, report_file, plots_dir, schema=target_schema)

    print(f"\n[OK] Relatório TPC-DS gerado: {report_file}")
    print(f"[OK] Gráficos salvos em: {plots_dir}/")
    return 0


def main() -> int:
    args = arguments()
    settings = TrinoSettings.from_environment(
        output_dir=args.output_dir,
        iterations=args.iterations,
        scale_factor=args.scale_factor,
        benchmark_type="tpcds",
    )
    return run_tpcds(
        settings=settings,
        setup=args.setup,
        replace=args.replace,
        continue_on_setup_errors=args.continue_on_setup_errors,
        output_dir=args.output_dir,
        report_path=args.report_path,
    )


if __name__ == "__main__":
    sys.exit(main())
