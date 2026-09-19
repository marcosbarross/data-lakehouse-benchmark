"""Configuração comum, sempre sobrescrevível por ambiente ou CLI."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Carregar .env na raiz do projeto se existir
_root_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _root_env.exists():
    with open(_root_env) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _k, _v = _line.split('=', 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class TrinoSettings:
    host: str
    port: int
    user: str
    source_catalog: str
    source_schema: str
    scale_factor: str
    benchmark_type: str
    bucket: str
    delta_storage_scheme: str
    iterations: int
    output_dir: Path

    @classmethod
    def from_environment(
        cls,
        output_dir: Path,
        iterations: int | None = None,
        scale_factor: str | None = None,
        benchmark_type: str | None = None,
    ) -> "TrinoSettings":
        sf = (scale_factor or os.getenv("BENCHMARK_SCALE_FACTOR", "sf1")).lower()
        if not sf.startswith("sf") and sf != "tiny":
            sf = f"sf{sf}"

        b_type = (benchmark_type or os.getenv("BENCHMARK_TYPE", "tpch")).lower()
        default_source_cat = "tpcds" if b_type == "tpcds" else "tpch"
        source_cat = os.getenv("BENCHMARK_SOURCE_CATALOG", default_source_cat)
        # Se scale_factor foi passado explicitamente, source_schema deve seguí-lo.
        # BENCHMARK_SOURCE_SCHEMA do .env só é usado quando scale_factor não é fornecido.
        if scale_factor is not None:
            source_sch = sf
        else:
            source_sch = os.getenv("BENCHMARK_SOURCE_SCHEMA", sf)

        return cls(
            host=os.getenv("TRINO_HOST", "192.168.56.80"),
            port=int(os.getenv("TRINO_PORT", "30080")),
            user=os.getenv("TRINO_USER", "trino"),
            source_catalog=source_cat,
            source_schema=source_sch,
            scale_factor=sf,
            benchmark_type=b_type,
            bucket=os.getenv("MINIO_BUCKET", "warehouse"),
            delta_storage_scheme=os.getenv("DELTA_STORAGE_SCHEME", "s3a"),
            iterations=iterations or int(os.getenv("BENCHMARK_ITERATIONS", "3")),
            output_dir=output_dir,
        )

    def target_schema(self, variant: str = "") -> str:
        """Retorna o nome padronizado do schema no Lakehouse."""
        env_override = os.getenv("BENCHMARK_TARGET_SCHEMA")
        if env_override and not variant:
            return env_override
        if variant:
            return f"{variant}_{self.scale_factor}"
        return f"{self.benchmark_type}_{self.scale_factor}"
