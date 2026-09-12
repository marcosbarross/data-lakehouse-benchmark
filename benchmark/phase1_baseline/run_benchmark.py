"""Executor da Fase 1 — Baseline Geral TPC-H SF1 (Iceberg vs Delta Lake)."""
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
from benchmark.phase1_baseline.queries import TPCH_QUERIES
from benchmark.phase1_baseline.reporting import generate_markdown_report, generate_plots
from benchmark.phase1_baseline.setup import prepare

BENCHMARK_SCHEMA = os.getenv("BENCHMARK_SCHEMA", "benchmark")
CATALOGS = ["iceberg", "delta_lake"]


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Fase 1 — Baseline Geral TPC-H SF1")
    parser.add_argument("--setup", action="store_true", help="Cria tabelas de baseline nos catalogos Iceberg e Delta Lake")
    parser.add_argument("--replace", action="store_true", help="Remove tabelas existentes antes do setup (requer --setup)")
    parser.add_argument("--iterations", type=int, default=None, help="Numero de iteracoes por consulta")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results/tpch_sf1"), help="Diretorio de saida dos graficos e dados brutos")
    parser.add_argument("--report-path", type=Path, default=None, help="Caminho do relatorio Markdown gerado")
    parser.add_argument("--schema", type=str, default=BENCHMARK_SCHEMA, help="Nome do schema de benchmark")
    parser.add_argument("--continue-on-setup-errors", action="store_true", help="Continua mesmo se houver erros no setup")
    return parser.parse_args()


def run_phase1(
    settings: TrinoSettings,
    setup: bool = False,
    replace: bool = False,
    continue_on_setup_errors: bool = False,
    output_dir: Path | None = None,
    report_path: Path | None = None,
    schema: str | None = None,
    runs_collector: list[dict[str, Any]] | None = None,
) -> int:
    """Executa a suíte de baseline da Fase 1."""
    target_schema = schema or (settings.target_schema() if settings.scale_factor != "sf1" else BENCHMARK_SCHEMA)
    plots_dir = output_dir or Path(f"benchmark_results/tpch_{settings.scale_factor.lower()}")
    report_file = report_path or (plots_dir / "benchmark_report.md")
    plots_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"BENCHMARK FASE 1: BASELINE TPC-H {settings.scale_factor.upper()} (ICEBERG vs DELTA LAKE)")
    print("=" * 70)

    client = TrinoClient(settings)

    # Auto-detecção de tabelas faltantes
    if not setup:
        missing: list[str] = []
        for cat in CATALOGS:
            for probe_table in ("lineitem", "orders"):
                chk = client.execute(f"SELECT 1 FROM {cat}.{target_schema}.{probe_table} LIMIT 1", catalog=cat)
                if chk.error:
                    missing.append(f"{cat}.{target_schema}.{probe_table}")
        if missing:
            print(f"\n[AVISO] Tabelas de baseline não encontradas em: {missing[:2]}")
            print(f"[AUTO-SETUP] Executando o provisionamento dos dados automaticamente...")
            setup = True

    if setup:
        errors = prepare(settings, replace=replace, schema=target_schema)
        if errors:
            write_json(plots_dir / "setup_errors.json", errors)
            print(f"[AVISO] Setup finalizado com {len(errors)} erro(s).")
            if not continue_on_setup_errors:
                print("[ERRO] Abortando benchmark devido a falhas no setup.")
                return 1
    results: dict[str, Any] = {catalog: {} for catalog in CATALOGS}
    raw_runs: list[dict[str, Any]] = []

    for catalog in CATALOGS:
        print(f"\n[BENCHMARK FASE 1] Executando consultas no catálogo '{catalog}'...")
        for query_name, query_template in TPCH_QUERIES.items():
            sql = query_template.format(catalog=catalog, schema=target_schema)
            print(f"  [EXEC] {query_name} em {catalog}...")
            times: list[float] = []

            for iteration in range(1, settings.iterations + 1):
                res = client.execute(sql, catalog=catalog)
                raw_runs.append({
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "catalog": catalog,
                    "suite": "phase1_baseline",
                    "benchmark": "tpch",
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
                print(f"    [OK] Media: {results[catalog][query_name]['avg_time']:.3f}s")

    # Gravar execuções brutas
    write_csv(plots_dir / "runs.csv", raw_runs)
    write_json(plots_dir / "runs.json", raw_runs)

    if runs_collector is not None:
        runs_collector.extend(raw_runs)

    # Gerar gráficos e relatório
    has_results = any(bool(results[cat]) for cat in CATALOGS)
    if has_results:
        generate_plots(results, plots_dir)
        generate_markdown_report(results, plots_dir, settings, report_path=report_file, schema=schema)
        print(f"\n[OK] Fase 1 concluída com sucesso!")
        print(f"[OK] Gráficos salvos em: {plots_dir}/")
        print(f"[OK] Relatório salvo em: {report_file}")
        return 0
    else:
        print("\n[ERRO] Benchmark Fase 1 falhou sem consultas bem-sucedidas.")
        return 1


def main() -> int:
    args = arguments()
    if args.replace and not args.setup:
        raise SystemExit("--replace só pode ser usado junto com --setup")

    settings = TrinoSettings.from_environment(args.output_dir, args.iterations)
    return run_phase1(
        settings=settings,
        setup=args.setup,
        replace=args.replace,
        continue_on_setup_errors=args.continue_on_setup_errors,
        output_dir=args.output_dir,
        report_path=args.report_path,
        schema=args.schema,
    )


if __name__ == "__main__":
    raise SystemExit(main())
