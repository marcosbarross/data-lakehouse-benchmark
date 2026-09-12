"""Cria cópias isoladas de controle e otimizadas, sem tocar no baseline."""
from __future__ import annotations

from benchmark.common.config import TrinoSettings
from benchmark.common.trino_client import TrinoClient

TABLES = ("region", "nation", "supplier", "part", "partsupp", "customer", "orders", "lineitem")


def _schema_location(settings: TrinoSettings, variant: str) -> str:
    return f"{settings.delta_storage_scheme}://{settings.bucket}/benchmark_phase2_delta/{variant}/"


def get_variant_schema(variant: str, scale_factor: str) -> str:
    if scale_factor == "sf1":
        return variant
    return f"{variant}_{scale_factor}"


def prepare(settings: TrinoSettings, replace: bool = False) -> list[str]:
    client = TrinoClient(settings)
    errors: list[str] = []
    print(f"\n[STAGING FASE 2] Preparando schemas de Otimização (SF: {settings.scale_factor.upper()})...")

    for catalog in ("iceberg", "delta_lake"):
        for base_variant in ("phase2_control", "phase2_optimized"):
            variant = get_variant_schema(base_variant, settings.scale_factor)
            if replace:
                print(f"  [DROP] Removendo schema {catalog}.{variant}...")
                dropped = client.execute(f"DROP SCHEMA IF EXISTS {catalog}.{variant} CASCADE", catalog)
                if dropped.error:
                    errors.append(f"{catalog}.{variant}: {dropped.error}")

            schema_sql = f"CREATE SCHEMA IF NOT EXISTS {catalog}.{variant}"
            if catalog == "delta_lake":
                schema_sql += f" WITH (location = '{_schema_location(settings, variant)}')"
            result = client.execute(schema_sql, catalog)
            if result.error:
                errors.append(f"{catalog}.{variant}: {result.error}")
                continue

            for table in TABLES:
                qualified = f"{catalog}.{variant}.{table}"
                # Verificar se tabela já existe
                exists_chk = client.execute(f"SELECT 1 FROM {qualified} LIMIT 1", catalog)
                if not replace and not exists_chk.error:
                    print(f"  [OK] {qualified} já existe")
                    continue

                source = f"{settings.source_catalog}.{settings.source_schema}.{table}"
                properties = ""
                if base_variant == "phase2_optimized" and catalog == "iceberg":
                    if table == "lineitem":
                        properties = " WITH (partitioning = ARRAY['month(shipdate)'])"
                    elif table == "customer":
                        properties = " WITH (partitioning = ARRAY['mktsegment'])"
                elif base_variant == "phase2_optimized" and catalog == "delta_lake" and table == "customer":
                    properties = " WITH (partitioned_by = ARRAY['mktsegment'])"

                print(f"  [CRIANDO] {qualified} a partir de {source}...")
                result = client.execute(f"CREATE TABLE IF NOT EXISTS {qualified}{properties} AS SELECT * FROM {source}", catalog)
                if result.error:
                    print(f"  [ERRO] Falha ao criar {qualified}: {result.error}")
                    errors.append(f"{qualified}: {result.error}")
                else:
                    print(f"  [OK] {qualified} criada com sucesso")
    return errors

