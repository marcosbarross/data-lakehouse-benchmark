# Benchmark Comparativo - Iceberg vs Delta Lake

**Data:** 2026-08-17 16:54:47

## Configuracao do Ambiente

- **Host Trino:** 192.168.56.80:30080
- **Schema:** benchmark
- **Iteracoes por query:** 3
- **Catalogo Iceberg:** Apache Iceberg (S3/MinIO)
- **Catalogo Delta Lake:** Delta Lake (S3/MinIO)
- **Infraestrutura:** k3s rodando em Vagrant (VirtualBox)
  - k3s-master: 2 vCPUs, 2GB RAM
  - k3s-worker1: 2 vCPUs, 8GB RAM
  - k3s-worker2: 2 vCPUs, 4GB RAM
- **Dataset:** TPC-H com Fator de Escala 1 (~1GB)

## Visao Geral dos Resultados

- **Tempo total Iceberg:** 9.36s
- **Tempo total Delta Lake:** 9.79s
- **Melhor performer geral:** Iceberg (4.3% mais rapido)

## Tabela Comparativa Detalhada

| Query | Iceberg (s) | Delta Lake (s) | Speedup Delta | Vencedor |
|-------|-------------|----------------|---------------|----------|
| Q1 | 0.67 | 0.60 | 1.13x | Delta Lake |
| Q2 | 0.59 | 0.65 | 0.91x | Iceberg |
| Q3 | 0.90 | 0.78 | 1.16x | Delta Lake |
| Q4 | 0.62 | 0.73 | 0.86x | Iceberg |
| Q5 | 1.11 | 1.15 | 0.97x | Iceberg |
| Q6 | 0.28 | 0.37 | 0.77x | Iceberg |
| Q7 | 0.99 | 1.07 | 0.93x | Iceberg |
| Q8 | 1.42 | 1.65 | 0.86x | Iceberg |
| Q9 | 1.62 | 1.69 | 0.96x | Iceberg |
| Q10 | 1.15 | 1.11 | 1.04x | Delta Lake |

**Resumo:** Delta Lake venceu em 3 queries, Iceberg venceu em 7 queries.

## Graficos

### Comparacao de Tempo Medio por Query

![Iceberg vs Delta Lake](benchmark_plots/iceberg_vs_deltalake.png)

### Speedup Relativo do Delta Lake em relacao ao Iceberg

![Speedup](benchmark_plots/speedup_deltalake_vs_iceberg.png)

### Tempo Total Acumulado

![Tempo Total](benchmark_plots/total_time_comparison.png)

## Estatisticas Descritivas


### Iceberg

| Query | Media (s) | Min (s) | Max (s) | Desvio Padrao (s) |
|-------|-----------|---------|---------|-------------------|
| Q1 | 0.67 | 0.54 | 0.75 | 0.12 |
| Q2 | 0.59 | 0.56 | 0.61 | 0.03 |
| Q3 | 0.90 | 0.79 | 1.07 | 0.15 |
| Q4 | 0.62 | 0.56 | 0.68 | 0.06 |
| Q5 | 1.11 | 1.07 | 1.17 | 0.05 |
| Q6 | 0.28 | 0.24 | 0.32 | 0.04 |
| Q7 | 0.99 | 0.78 | 1.14 | 0.18 |
| Q8 | 1.42 | 1.35 | 1.54 | 0.10 |
| Q9 | 1.62 | 1.46 | 1.81 | 0.18 |
| Q10 | 1.15 | 1.14 | 1.17 | 0.01 |

### Delta Lake

| Query | Media (s) | Min (s) | Max (s) | Desvio Padrao (s) |
|-------|-----------|---------|---------|-------------------|
| Q1 | 0.60 | 0.53 | 0.64 | 0.06 |
| Q2 | 0.65 | 0.53 | 0.74 | 0.11 |
| Q3 | 0.78 | 0.76 | 0.80 | 0.02 |
| Q4 | 0.73 | 0.56 | 0.81 | 0.14 |
| Q5 | 1.15 | 1.00 | 1.22 | 0.13 |
| Q6 | 0.37 | 0.32 | 0.45 | 0.07 |
| Q7 | 1.07 | 0.87 | 1.22 | 0.18 |
| Q8 | 1.65 | 1.50 | 1.92 | 0.23 |
| Q9 | 1.69 | 1.64 | 1.73 | 0.04 |
| Q10 | 1.11 | 1.07 | 1.14 | 0.03 |

## Conclusao

Neste benchmark com 10 queries do TPC-H executadas 3 vezes cada, o **Iceberg** apresentou melhor performance geral, sendo 4.3% mais rapido que o concorrente no tempo acumulado.

Observacoes:
- As tabelas foram criadas em ambos catalogos a partir do dataset sintetico TPC-H SF1 (~1GB).
- O staging e a execucao foram totalmente automatizados via Python.
- Os dados residem no MinIO em formato Parquet, gerenciados pelos respectivos metadados de cada engine.