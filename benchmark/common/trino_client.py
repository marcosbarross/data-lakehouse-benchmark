"""Adaptador pequeno para o Trino DBAPI, com retentativas e coleta de plano."""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from trino.dbapi import connect

from .config import TrinoSettings


@dataclass
class StatementResult:
    elapsed_seconds: float
    row_count: int
    planning_time_ms: float = 0.0
    analysis_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    physical_input_bytes: int = 0
    processed_bytes: int = 0
    peak_memory_bytes: int = 0
    splits_count: int = 0
    error: str | None = None


class TrinoClient:
    def __init__(self, settings: TrinoSettings, retries: int = 2) -> None:
        self.settings = settings
        self.retries = retries

    def execute(self, sql: str, catalog: str | None = None, fetch: bool = True) -> StatementResult:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            started = time.perf_counter()
            try:
                connection = connect(
                    host=self.settings.host, port=self.settings.port,
                    user=self.settings.user, catalog=catalog,
                )
                cursor = connection.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall() if fetch else []

                # Extrai estatísticas detalhadas de execução e catálogo da API do Trino
                stats = getattr(cursor._query, "stats", {}) if hasattr(cursor, "_query") else {}
                planning_ms = float(stats.get("planningTimeMillis") or 0.0)
                analysis_ms = float(stats.get("analysisTimeMillis") or 0.0)
                elapsed_ms = float(stats.get("elapsedTimeMillis") or (time.perf_counter() - started) * 1000.0)
                exec_ms = max(0.0, elapsed_ms - planning_ms)
                cpu_ms = float(stats.get("cpuTimeMillis") or 0.0)
                physical_bytes = int(stats.get("physicalInputBytes") or 0)
                processed_bytes = int(stats.get("processedBytes") or 0)
                peak_mem = int(stats.get("peakMemoryBytes") or 0)
                splits = int(stats.get("completedSplits") or stats.get("totalSplits") or 0)

                cursor.close()
                connection.close()

                return StatementResult(
                    elapsed_seconds=round(elapsed_ms / 1000.0, 6) if elapsed_ms else round(time.perf_counter() - started, 6),
                    row_count=len(rows),
                    planning_time_ms=round(planning_ms, 2),
                    analysis_time_ms=round(analysis_ms, 2),
                    execution_time_ms=round(exec_ms, 2),
                    cpu_time_ms=round(cpu_ms, 2),
                    physical_input_bytes=physical_bytes,
                    processed_bytes=processed_bytes,
                    peak_memory_bytes=peak_mem,
                    splits_count=splits,
                )
            except Exception as exc:  # DBAPI exposes vendor-specific exceptions.
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
        return StatementResult(time.perf_counter() - started, 0, error=str(last_error))

    def explain_analyze(self, sql: str, catalog: str) -> tuple[str | None, str | None]:
        """Executa o plano uma vez; EXPLAIN ANALYZE já executa a consulta."""
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                connection = connect(host=self.settings.host, port=self.settings.port,
                                     user=self.settings.user, catalog=catalog)
                cursor = connection.cursor()
                cursor.execute(f"EXPLAIN ANALYZE {sql}")
                plan = "\n".join(str(row[0]) for row in cursor.fetchall())
                cursor.close()
                connection.close()
                return plan, None
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1 + attempt)
        return None, str(last_error)


def plan_metrics(plan: str | None) -> dict[str, int | None]:
    """Extrai métricas apenas quando a versão do Trino as publica no plano."""
    if not plan:
        return {"input_rows": None, "input_bytes": None, "files": None}
    patterns: dict[str, str] = {
        "input_rows": r"Input:\s*([\d,]+)\s+rows",
        "input_bytes": r"Input:\s*[\d,]+\s+rows\s*\(([^)]+)\)",
        "files": r"(?:files|splits)\s*[=:]\s*([\d,]+)",
    }
    metrics: dict[str, int | None] = {"input_rows": None, "input_bytes": None, "files": None}
    for key, pattern in patterns.items():
        match = re.search(pattern, plan, flags=re.IGNORECASE)
        if match and key != "input_bytes":
            metrics[key] = int(match.group(1).replace(",", ""))
        elif match and key == "input_bytes":
            metrics[key] = _parse_bytes(match.group(1))
    return metrics


def _parse_bytes(value: str) -> int | None:
    match = re.fullmatch(r"\s*([\d.]+)\s*([KMGTPE]?B)\s*", value, flags=re.IGNORECASE)
    if not match:
        return None
    units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4,
             "PB": 1024**5, "EB": 1024**6}
    return int(float(match.group(1)) * units[match.group(2).upper()])
