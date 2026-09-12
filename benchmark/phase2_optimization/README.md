# Fase 2 — Otimização de leitura e data skipping

Esta fase cria cópias isoladas do baseline: `phase2_control` e `phase2_optimized` em cada catálogo. Ela nunca altera o schema `benchmark`.

## Execução

Recomenda-se utilizar o ponto único de entrada na raiz do projeto:

```bash
# Executar apenas a Fase 2 através da CLI unificada:
python run_benchmark.py --suite phase2 --setup

# Ou diretamente pelo módulo:
python -m benchmark.phase2_optimization.run_benchmark --setup
```

Para recriar apenas os schemas da fase, use `--setup --replace`. Essa opção remove exclusivamente `iceberg.phase2_*` e `delta_lake.phase2_*`.

As configurações aceitam `TRINO_HOST`, `TRINO_PORT`, `TRINO_USER`,
`BENCHMARK_SOURCE_CATALOG`, `BENCHMARK_SOURCE_SCHEMA`, `MINIO_BUCKET`,
`DELTA_STORAGE_SCHEME` e `BENCHMARK_ITERATIONS`; argumentos da CLI têm precedência onde aplicável.
Por padrão, a fonte é `tpch.sf1`. Para reutilizar o baseline já materializado, defina
`BENCHMARK_SOURCE_CATALOG=iceberg` ou `delta_lake` e `BENCHMARK_SOURCE_SCHEMA=benchmark`
conforme o catálogo escolhido.

## Desenho do teste

- **Iceberg otimizado:** `month(shipdate)` (particionamento oculto) em `lineitem` e `mktsegment` em `customer`.
- **Delta no Trino:** `mktsegment` em `customer`. O conector Delta Lake do Trino 483 não executa `OPTIMIZE ... ZORDER BY`; portanto esse passo deve rodar em Spark/Databricks ou outro mecanismo Delta compatível. O SQL de referência está em `setup_tables.sql`.
- **Consultas:** Q3, Q6 e Q7 medem filtros ligados a `shipdate`/`mktsegment`; Q19 é o controle com filtros não particionados.

Os dados brutos são gravados em `results/runs.csv` e `results/runs.json`; os planos em `results/plans/`. `summary.md` e `speedup.png` são os artefatos comparativos.
