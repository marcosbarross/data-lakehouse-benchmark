"""Pacote de benchmarks reproduzíveis para o Lakehouse (Iceberg vs Delta Lake)."""
from __future__ import annotations

from typing import Any

__all__ = ["run_phase1", "run_phase2"]


def __getattr__(name: str) -> Any:
    if name == "run_phase1":
        from benchmark.phase1_baseline.run_benchmark import run_phase1
        return run_phase1
    if name == "run_phase2":
        from benchmark.phase2_optimization.run_benchmark import run_phase2
        return run_phase2
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
