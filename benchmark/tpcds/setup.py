"""Staging de dados do TPC-DS nos catálogos Iceberg e Delta Lake."""
from __future__ import annotations

import re
from trino.dbapi import connect

from benchmark.common.config import TrinoSettings
from benchmark.tpcds.queries import TPCDS_TABLES

CATALOGS = ["iceberg", "delta_lake"]


def get_delta_table_location(settings: TrinoSettings, bucket: str, schema: str, table: str) -> str:
    return f"{settings.delta_storage_scheme}://{bucket}/{schema}_delta/{table}"


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


def prepare(settings: TrinoSettings, replace: bool = False, schema: str | None = None) -> list[str]:
    """Cria schemas e tabelas para a suíte TPC-DS nos catálogos Iceberg e Delta Lake."""
    target_schema = schema or settings.target_schema()
    errors: list[str] = []
    print(f"\n[STAGING TPC-DS] Iniciando preparação dos dados (Schema: '{target_schema}', SF: '{settings.scale_factor}')...")

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
        if replace:
            print("[STAGING TPC-DS] Opção --replace ativada. Removendo tabelas existentes...")
            for catalog in CATALOGS:
                if schema_exists(cursor, catalog, target_schema):
                    for table in reversed(TPCDS_TABLES):
                        if table_exists(cursor, catalog, target_schema, table):
                            print(f"  [DROP] Removendo {catalog}.{target_schema}.{table}...")
                            try:
                                cursor.execute(f"DROP TABLE IF EXISTS {catalog}.{target_schema}.{table}")
                            except Exception as e:
                                errors.append(f"Erro ao remover {catalog}.{target_schema}.{table}: {e}")

        # Configurar Iceberg Schema
        if not schema_exists(cursor, "iceberg", target_schema):
            print(f"[STAGING TPC-DS] Criando schema iceberg.{target_schema}...")
            try:
                cursor.execute(f"CREATE SCHEMA iceberg.{target_schema}")
            except Exception as e:
                errors.append(f"Falha ao criar schema iceberg.{target_schema}: {e}")

        bucket = settings.bucket
        print(f"[STAGING TPC-DS] Bucket MinIO definido: {bucket}")

        # Configurar Delta Lake Schema
        if not schema_exists(cursor, "delta_lake", target_schema):
            print(f"[STAGING TPC-DS] Criando schema delta_lake.{target_schema}...")
            try:
                cursor.execute(
                    f"CREATE SCHEMA delta_lake.{target_schema} "
                    f"WITH (location = '{settings.delta_storage_scheme}://{bucket}/{target_schema}_delta/')"
                )
            except Exception as e:
                errors.append(f"Falha ao criar schema delta_lake.{target_schema}: {e}")

        source = f"tpcds.{settings.scale_factor}"
        for catalog in CATALOGS:
            print(f"\n[STAGING TPC-DS] Verificando tabelas em {catalog}.{target_schema} (Origem: {source})...")
            for table in TPCDS_TABLES:
                if table_exists(cursor, catalog, target_schema, table):
                    print(f"  [OK] {table} já existe em {catalog}")
                else:
                    print(f"  [CRIANDO] {table} em {catalog} a partir de {source}.{table}...")
                    try:
                        if catalog == "delta_lake":
                            table_location = get_delta_table_location(settings, bucket, target_schema, table)
                            cursor.execute(
                                f"CREATE TABLE {catalog}.{target_schema}.{table} "
                                f"WITH (location = '{table_location}') "
                                f"AS SELECT * FROM {source}.{table}"
                            )
                        else:
                            cursor.execute(
                                f"CREATE TABLE {catalog}.{target_schema}.{table} "
                                f"AS SELECT * FROM {source}.{table}"
                            )
                        print(f"  [OK] {table} criada com sucesso em {catalog}")
                    except Exception as e:
                        msg = f"Falha ao criar {catalog}.{target_schema}.{table}: {e}"
                        print(f"  [ERRO] {msg}")
                        errors.append(msg)
    finally:
        cursor.close()
        conn.close()

    if not errors:
        print("\n[STAGING TPC-DS] Todos os dados da suíte TPC-DS estão prontos!")
    else:
        print(f"\n[STAGING TPC-DS] Finalizado com {len(errors)} erro(s).")
    return errors
