"""Staging de dados do TPC-H SF1 nos catálogos Iceberg e Delta Lake."""
from __future__ import annotations

import os
import re
from typing import Sequence

from trino.dbapi import connect

from benchmark.common.config import TrinoSettings
from benchmark.phase1_baseline.queries import TABLES

BENCHMARK_SCHEMA = os.getenv("BENCHMARK_SCHEMA", "benchmark")
CATALOGS = ["iceberg", "delta_lake"]


def get_delta_table_location(settings: TrinoSettings, bucket: str, schema: str, table: str) -> str:
    folder = "benchmark_delta" if schema == "benchmark" else f"{schema}_delta"
    return f"{settings.delta_storage_scheme}://{bucket}/{folder}/{table}"


def schema_exists(cursor, catalog: str, schema: str) -> bool:
    try:
        cursor.execute(f"SHOW SCHEMAS IN {catalog}")
        schemas = [row[0] for row in cursor.fetchall()]
        return schema in schemas
    except Exception:
        return False


def table_exists(cursor, catalog: str, schema: str, table: str) -> bool:
    try:
        cursor.execute(f"SHOW TABLES IN {catalog}.{schema}")
        tables = [row[0] for row in cursor.fetchall()]
        return table in tables
    except Exception:
        return False


def get_bucket_from_iceberg(cursor, schema: str) -> str | None:
    try:
        cursor.execute(f"SHOW CREATE SCHEMA iceberg.{schema}")
        result = cursor.fetchall()
        create_sql = result[0][0]
        match = re.search(r"s3(?:a)?://([^/]+)", create_sql)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None


def prepare(settings: TrinoSettings, replace: bool = False, schema: str = BENCHMARK_SCHEMA) -> list[str]:
    """Cria schemas e tabelas para a Fase 1 (Baseline) nos catálogos Iceberg e Delta Lake."""
    errors: list[str] = []
    print(f"\n[STAGING FASE 1] Iniciando preparacao dos dados (Schema: '{schema}')...")

    try:
        conn = connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            catalog="system",
            schema="default",
        )
    except Exception as exc:
        msg = f"Falha ao conectar no Trino ({settings.host}:{settings.port}): {exc}"
        print(f"[ERRO] {msg}")
        return [msg]

    cursor = conn.cursor()

    try:
        # Se replace for solicitado, descartar tabelas dos catálogos
        if replace:
            print("[STAGING FASE 1] Opção --replace ativada. Removendo tabelas existentes...")
            for catalog in CATALOGS:
                if schema_exists(cursor, catalog, schema):
                    for table in reversed(TABLES):
                        if table_exists(cursor, catalog, schema, table):
                            print(f"  [DROP] Removendo {catalog}.{schema}.{table}...")
                            try:
                                cursor.execute(f"DROP TABLE IF EXISTS {catalog}.{schema}.{table}")
                            except Exception as e:
                                errors.append(f"Erro ao remover {catalog}.{schema}.{table}: {e}")

        # Configurar Iceberg
        iceberg_schema_exists = schema_exists(cursor, "iceberg", schema)
        bucket: str | None = None
        if iceberg_schema_exists:
            bucket = get_bucket_from_iceberg(cursor, schema)

        if not iceberg_schema_exists:
            print(f"[STAGING FASE 1] Criando schema iceberg.{schema}...")
            try:
                cursor.execute(f"CREATE SCHEMA iceberg.{schema}")
            except Exception as e:
                errors.append(f"Falha ao criar schema iceberg.{schema}: {e}")

        if not bucket:
            bucket = settings.bucket
        print(f"[STAGING FASE 1] Bucket MinIO definido: {bucket}")

        # Configurar Delta Lake
        delta_schema_exists = schema_exists(cursor, "delta_lake", schema)
        delta_folder = "benchmark_delta" if schema == "benchmark" else f"{schema}_delta"
        if not delta_schema_exists:
            print(f"[STAGING FASE 1] Criando schema delta_lake.{schema}...")
            try:
                cursor.execute(
                    f"CREATE SCHEMA delta_lake.{schema} "
                    f"WITH (location = '{settings.delta_storage_scheme}://{bucket}/{delta_folder}/')"
                )
            except Exception as e:
                errors.append(f"Falha ao criar schema delta_lake.{schema}: {e}")

        # Criar tabelas nos dois catalogos
        source = f"{settings.source_catalog}.{settings.source_schema}"
        for catalog in CATALOGS:
            print(f"\n[STAGING FASE 1] Verificando tabelas em {catalog}.{schema} (Origem: {source})...")
            for table in TABLES:
                if table_exists(cursor, catalog, schema, table):
                    print(f"  [OK] {table} já existe em {catalog}")
                else:
                    print(f"  [CRIANDO] {table} em {catalog} a partir de {source}.{table}...")
                    try:
                        if catalog == "delta_lake":
                            table_location = get_delta_table_location(settings, bucket, schema, table)
                            cursor.execute(
                                f"CREATE TABLE {catalog}.{schema}.{table} "
                                f"WITH (location = '{table_location}') "
                                f"AS SELECT * FROM {source}.{table}"
                            )
                        else:
                            cursor.execute(
                                f"CREATE TABLE {catalog}.{schema}.{table} "
                                f"AS SELECT * FROM {source}.{table}"
                            )
                        print(f"  [OK] {table} criada com sucesso em {catalog}")
                    except Exception as e:
                        msg = f"Falha ao criar {catalog}.{schema}.{table}: {e}"
                        print(f"  [ERRO] {msg}")
                        errors.append(msg)
    finally:
        cursor.close()
        conn.close()

    if not errors:
        print("\n[STAGING FASE 1] Todos os dados da Fase 1 estao prontos!")
    else:
        print(f"\n[STAGING FASE 1] Finalizado com {len(errors)} erro(s).")
    return errors
