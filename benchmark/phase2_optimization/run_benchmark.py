"""CLI da Fase 2. Exemplo: python -m benchmark.phase2_optimization.run_benchmark --setup"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Garante que a raiz do repositório esteja no sys.path, permitindo execução de qualquer diretório
_repo_root = Path(__file__).resolve().parent.parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from benchmark.common.config import TrinoSettings
from benchmark.common.results import write_csv, write_json
from benchmark.common.trino_client import TrinoClient, plan_metrics

try:
    from .queries import QUERIES
    from .reporting import create_artifacts
    from .setup import prepare
except ImportError:
    from benchmark.phase2_optimization.queries import QUERIES
    from benchmark.phase2_optimization.reporting import create_artifacts
    from benchmark.phase2_optimization.setup import prepare


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Fase 2 — Iceberg vs Delta")
    parser.add_argument("--setup", action="store_true", help="Cria tabelas isoladas da Fase 2")
    parser.add_argument("--replace", action="store_true", help="Remove schemas phase2 antes do setup (requer --setup)")
    parser.add_argument("--iterations", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results/phase2_sf1"))
    parser.add_argument("--skip-explain", action="store_true")
    parser.add_argument("--continue-on-setup-errors", action="store_true",
                        help="Continua mesmo se o setup falhar (útil apenas para diagnóstico)")
    return parser.parse_args()


def run_phase2(
    settings: TrinoSettings,
    setup: bool = False,
    replace: bool = False,
    continue_on_setup_errors: bool = False,
    output_dir: Path | None = None,
    skip_explain: bool = False,
    runs_collector: list[dict[str, Any]] | None = None,
) -> int:
    target_dir = output_dir or settings.output_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("BENCHMARK FASE 2: OTIMIZAÇÃO & DATA SKIPPING (ICEBERG vs DELTA LAKE)")
    print("=" * 70)

    client = TrinoClient(settings)

    # Auto-detecção de schemas/tabelas da Fase 2
    if not setup:
        missing: list[str] = []
        for catalog in ("iceberg", "delta_lake"):
            for variant in ("control", "optimized"):
                schema = (
                    f"phase2_{variant}"
                    if settings.scale_factor == "sf1"
                    else f"phase2_{variant}_{settings.scale_factor}"
                )
                chk = client.execute(f"SELECT 1 FROM {catalog}.{schema}.lineitem LIMIT 1", catalog)
                if chk.error:
                    missing.append(f"{catalog}.{schema}.lineitem")
        if missing:
            print(f"\n[AVISO] Tabelas da Fase 2 ({settings.scale_factor.upper()}) não encontradas: {missing[:2]}")
            print(f"[AUTO-SETUP] Executando o provisionamento dos dados da Fase 2 automaticamente...")
            setup = True

    if setup:
        errors = prepare(settings, replace=replace)
        write_json(target_dir / "setup_errors.json", errors)
        if errors:
            print(f"[AVISO] Setup Fase 2 finalizado com {len(errors)} erro(s); consulte setup_errors.json.")
            if not continue_on_setup_errors:
                print("[ERRO] Abortando benchmark Fase 2 devido a falhas no setup.")
                return 1

    rows: list[dict[str, object]] = []
    plans_dir = target_dir / "plans"
    for catalog in ("iceberg", "delta_lake"):
        for variant in ("control", "optimized"):
            schema = (
                f"phase2_{variant}"
                if settings.scale_factor == "sf1"
                else f"phase2_{variant}_{settings.scale_factor}"
            )
            for name, template in QUERIES.items():
                sql = template.format(catalog=catalog, schema=schema)
                plan, plan_error = (None, None) if skip_explain else client.explain_analyze(sql, catalog)
                if plan:
                    plans_dir.mkdir(parents=True, exist_ok=True)
                    (plans_dir / f"{catalog}_{variant}_{name}.txt").write_text(plan, encoding="utf-8")
                metrics = plan_metrics(plan)
                for iteration in range(1, settings.iterations + 1):
                    result = client.execute(sql, catalog)
                    rows.append({
                        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                        "catalog": catalog,
                        "variant": variant,
                        "suite": "phase2_optimization",
                        "benchmark": "tpch",
                        "scale_factor": settings.scale_factor,
                        "query": name,
                        "iteration": iteration,
                        "elapsed_seconds": round(result.elapsed_seconds, 6),
                        "planning_time_ms": result.planning_time_ms,
                        "execution_time_ms": result.execution_time_ms,
                        "cpu_time_ms": result.cpu_time_ms,
                        "physical_input_bytes": result.physical_input_bytes or metrics["input_bytes"],
                        "peak_memory_bytes": result.peak_memory_bytes,
                        "splits_count": result.splits_count,
                        "row_count": result.row_count,
                        "input_rows": metrics["input_rows"],
                        "input_bytes": metrics["input_bytes"],
                        "files": metrics["files"],
                        "error": result.error or plan_error,
                    })
                    print(f"{catalog}/{variant}/{name} #{iteration}: {result.elapsed_seconds:.3f}s" +
                          (f" ERRO: {result.error}" if result.error else ""))
    write_csv(target_dir / "runs.csv", rows)
    write_json(target_dir / "runs.json", rows)
    if runs_collector is not None:
        runs_collector.extend(rows)
    create_artifacts(rows, target_dir)
    return 0 if any(not row["error"] for row in rows) else 1


def main() -> int:
    args = arguments()
    if args.replace and not args.setup:
        raise SystemExit("--replace só pode ser usado junto com --setup")
    settings = TrinoSettings.from_environment(args.output_dir, args.iterations)
    return run_phase2(
        settings=settings,
        setup=args.setup,
        replace=args.replace,
        continue_on_setup_errors=args.continue_on_setup_errors,
        output_dir=args.output_dir,
        skip_explain=args.skip_explain,
    )


if __name__ == "__main__":
    raise SystemExit(main())

