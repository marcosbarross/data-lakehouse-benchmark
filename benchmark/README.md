# 🚀 Suíte Unificada de Benchmarks do Lakehouse (Iceberg vs. Delta Lake)

Este diretório contém a suíte unificada, modular e reproduzível de benchmarks desenvolvida em Python para avaliar o desempenho entre **Apache Iceberg** e **Delta Lake** sobre o motor de consulta **Trino** e armazenamento de objetos compatível com S3 (**MinIO**) no Kubernetes (K3s).

A infraestrutura é provisionada de forma automatizada na **Magalu Cloud** via **OpenTofu** (`tofu/vms.tf`), com isolamento estrito entre nós de computação e armazenamento dedicado.

---

## 📑 Sumário

- [Visão Geral e Fases](#-visão-geral-e-fases)
- [Topologia de Infraestrutura (OpenTofu)](#-topologia-de-infraestrutura-opentofu)
- [Estrutura do Pacote](#-estrutura-do-pacote)
- [Pré-requisitos](#-pré-requisitos)
- [Como Executar (Ponto Único de Entrada)](#-como-executar-ponto-único-de-entrada)
  - [1. Ativar o Ambiente Virtual](#1-ativar-o-ambiente-virtual)
  - [2. Executar Todos os Benchmarks (Recomendado)](#2-executar-todos-os-benchmarks-recomendado)
  - [3. Executar Fases Específicas](#3-executar-fases-específicas)
  - [4. Recriar Schemas do Zero (Reset)](#4-recriar-schemas-do-zero-reset)
- [Opções da Linha de Comando (CLI)](#-opções-da-linha-de-comando-cli)
- [Desenho dos Testes](#-desenho-dos-testes)
  - [Fase 1 — Baseline Geral (TPC-H SF1)](#fase-1--baseline-geral-tpc-h-sf1)
  - [Fase 2 — Otimização e Data Skipping](#fase-2--otimização-e-data-skipping)
- [Artefatos e Resultados Gerados](#-artefatos-e-resultados-gerados)
- [Solução de Problemas (Troubleshooting)](#-solução-de-problemas-troubleshooting)

---

## 🎯 Visão Geral e Fases

A avaliação de desempenho é dividida em duas famílias de benchmark e múltiplas escalas de dados:

1. **Famílias de Benchmark Suportadas:**
   - **TPC-H (Relacional Analítico Geral):**
     - **Fase 1 — Baseline Geral (`benchmark/phase1_baseline`):** Tabelas planas out-of-the-box (Q1 a Q10).
     - **Fase 2 — Otimização e Data Skipping (`benchmark/phase2_optimization`):** Avalia particionamento temporal (*hidden partitioning* no Iceberg com `month(shipdate)`) e categórico (`mktsegment` no Delta Lake) comparando esquemas `control` vs `optimized` com `EXPLAIN ANALYZE`.
   - **TPC-DS (Decision Support - Padrão Moderno):**
     - Modelo dimensional realista corporativo (*Star/Snowflake Schema* com tabelas de fato como `store_sales` e dimensões `customer`, `item`, `date_dim`).
     - Consultas analíticas complexas com joins fato-dimensão e agrupamentos multidimensionais (Q3, Q7, Q19, Q26, Q42, Q52, Q55, Q73).

2. **Ordens de Grandeza de Dados (Scale Factors):**
   - **Pequeno (`SF1`):** ~1 GB de dados brutos (~300 MB Parquet por formato). Avalia latência mínima, planejamento de metadados e overhead do catálogo.
   - **Médio (`SF10`):** ~10 GB de dados brutos (~3 GB Parquet por formato). Avalia o throughput de leitura paralela e agregação distribuída.
   - **Grande (`SF100`):** ~100 GB de dados brutos (~25 a 30 GB Parquet por formato). Avalia I/O em larga escala e estresse de memória nos workers.

---

## 🖥️ Topologia de Infraestrutura (OpenTofu)

As máquinas virtuais são gerenciadas e provisionadas no OpenTofu (`tofu/vms.tf`) na Magalu Cloud com isolamento físico estrito:

| Instância / Hostname | Tipo de Máquina | vCPUs | RAM | Papel Arquitetural no Lakehouse |
| :--- | :--- | :---: | :---: | :--- |
| **`lakehouse-k3s-master`** | `BV2-4-40` | 2 | 4 GB | Control Plane K3s & Trino Coordinator |
| **`lakehouse-k3s-worker1`** | `BV4-8-100` | 4 | 8 GB | Storage Dedicado MinIO S3 (100 GB NVMe - Taint `dedicated=minio:NoSchedule`) |
| **`lakehouse-k3s-worker5`** | `BV2-4-40` | 2 | 4 GB | Catálogos Dedicados (Postgres + Hive) (Taint `dedicated=catalog:NoSchedule`) |
| **`lakehouse-k3s-worker2`** | `BV4-16-100` | 4 | 16 GB | Trino Compute Worker 1 (12 GB JVM Heap) |
| **`lakehouse-k3s-worker3`** | `BV4-16-100` | 4 | 16 GB | Trino Compute Worker 2 (12 GB JVM Heap) |
| **`lakehouse-k3s-worker4`** | `BV4-16-100` | 4 | 16 GB | Trino Compute Worker 3 (12 GB JVM Heap) |


O arquivo `.env` com os endereços de rede públicos e portas do Trino Coordinator e do MinIO é gerado automaticamente pelo OpenTofu após o `tofu apply`.

---

## 📁 Estrutura do Pacote

```text
benchmark/
├── __init__.py                    <- Exports das funções principais e lazy loader
├── __main__.py                    <- Ponto de entrada CLI (python -m benchmark)
├── README.md                      <- Este guia detalhado
├── common/                        <- Módulos utilitários compartilhados
│   ├── __init__.py
│   ├── config.py                  <- Leitura de variáveis de ambiente e .env
│   ├── trino_client.py            <- Cliente DBAPI com retentativas e parser EXPLAIN ANALYZE
│   └── results.py                 <- Persistência padronizada em CSV e JSON
├── phase1_baseline/               <- Módulo da Fase 1 (Baseline Geral TPC-H SF1)
│   ├── __init__.py
│   ├── queries.py                 <- Definição SQL parametrizada de Q1 a Q10
│   ├── setup.py                   <- Criação de schemas e tabelas baseline
│   ├── reporting.py               <- Gráficos (PNG) e relatório benchmark_report.md
│   └── run_benchmark.py           <- Runner isolado da Fase 1
└── phase2_optimization/           <- Módulo da Fase 2 (Otimizações de Leitura)
    ├── __init__.py
    ├── README.md                  <- Documentação complementar da Fase 2
    ├── queries.py                 <- Queries com particionamento (Q3, Q6, Q7, Q19)
    ├── setup.py                   <- Schemas phase2_control e phase2_optimized
    ├── setup_tables.sql           <- DDL de referência e notas de Z-Order
    ├── reporting.py               <- Sumário Markdown e gráficos de speedup
    ├── run_benchmark.py           <- Runner isolado da Fase 2
    └── results/                   <- Resultados, execuções e planos da Fase 2
```

Na raiz do repositório, encontra-se o script central:
- **`run_benchmark.py`**: Ponto único de entrada executável para orquestrar todas as etapas.

---

## 📋 Pré-requisitos

1. **Infraestrutura em Execução:**
   Cluster K3s ativo com os pods do Trino Coordinator, Trino Workers (3 nós) e MinIO em execução:
   ```bash
   # No diretório tofu/:
   tofu apply
   # No diretório raiz (aplicando Ansible):
   ansible-playbook -i ansible/inventory/hosts.magalu.yml ansible/site.yml
   ```

2. **Ambiente Virtual Python Configurado:**
   Instale as dependências:
   ```bash
   python3 -m venv env
   source env/bin/activate
   pip install -r requirements.txt
   ```

---

## 🚀 Como Executar (Ponto Único de Entrada)

### 1. Ativar o Ambiente Virtual

```bash
source env/bin/activate
```

### 2. Execução Padrão Unificada (Recomendado)

Ao executar sem argumentos, a suíte executa automaticamente **TPC-H (Fases 1 e 2)** e **TPC-DS** nas escalas **SF1 (~1 GB)** e **SF10 (~10 GB)** com **3 iterações** por consulta (o SF100 roda apenas quando solicitado explicitamente):

```bash
# Executa TPC-H + TPC-DS em SF1 e SF10 com auto-setup e 3 iterações:
python run_benchmark.py
```

### 3. Execuções Específicas e Escalas Individuais

```bash
# Executar apenas TPC-H em SF1:
python run_benchmark.py --benchmark tpch --scale-factor sf1

# Executar apenas TPC-DS em SF10:
python run_benchmark.py --benchmark tpcds --scale-factor sf10

# Executar grande escala SF100 sob demanda:
python run_benchmark.py --scale-factor sf100

# Executar apenas Fase 1 (Baseline) ou Fase 2 (Otimizações):
python run_benchmark.py --suite phase1
python run_benchmark.py --suite phase2
```

### 4. Modo Somente Relatório (Regerar Gráficos)

Para regerar o relatório consolidado e as 6 categorias de gráficos a partir de medições já salvas em disco sem reexecutar queries no Trino:

```bash
python run_benchmark.py --report-only
```

### 5. Recriar Schemas do Zero (Reset)

Para forçar a remoção e recriação das tabelas:

```bash
python run_benchmark.py --setup --replace
```

---

## ⚙️ Opções da Linha de Comando (CLI)

O comando `python run_benchmark.py` suporta os seguintes parâmetros:

| Argumento | Padrão | Descrição |
| :--- | :---: | :--- |
| `--benchmark {all,tpch,tpcds}` | `all` | Família de benchmark a executar (padrão: ambos TPC-H e TPC-DS) |
| `--scale-factor, --sf SF` | `None` | Scale factor único (ex: `sf1`, `sf10`, `sf100`). Sobrescreve `--scale-factors`. |
| `--scale-factors LIST` | `sf1,sf10` | Lista de scale factors separados por vírgula (padrão se omitido: `sf1,sf10`) |
| `--suite {all,phase1,phase2}` | `all` | Seleciona quais suítes TPC-H executar sequencialmente |
| `--setup` | `False` | Força recriação e carga (auto-detecção já provisiona se faltar tabela) |
| `--replace` | `False` | Descarta schemas/tabelas existentes antes do setup (requer `--setup`) |
| `--iterations N` | `3` | Número de repetições por consulta (padrão: 3 para rigor estatístico) |
| `--report-only` | `False` | Não executa queries; apenas consolida dados salvos e gera os 6 gráficos |
| `--skip-explain` | `False` | Pula a etapa de `EXPLAIN ANALYZE` na Fase 2 |
| `--continue-on-setup-errors` | `False` | Prossegue com o benchmark mesmo se houver falhas pontuais no setup |
| `--output-dir PATH` | `benchmark_results` | Diretório de saída dos gráficos consolidados e relatórios |
| `--report-path PATH` | `benchmark_results/benchmark_report.md` | Caminho do relatório comparativo consolidado mestre |
| `--output-dir-phase1 PATH` | `benchmark_results/tpch_<sf>` | Diretório de saída dos gráficos e dados brutos do TPC-H Fase 1 |
| `--output-dir-phase2 PATH` | `benchmark_results/phase2_<sf>` | Diretório de saída dos artefatos do TPC-H Fase 2 |
| `--output-dir-tpcds PATH` | `benchmark_results/tpcds_<sf>` | Diretório de saída dos artefatos e gráficos do TPC-DS |
| `--report-path-tpcds PATH` | `benchmark_results/tpcds_<sf>/...` | Caminho do relatório comparativo individual do TPC-DS |

---

## 🔬 Desenho dos Testes

### Fase 1 — Baseline Geral (TPC-H SF1)
Avalia o comportamento de Apache Iceberg e Delta Lake sem modificações de esquema ou índices de ordenação:
- **Catálogos:** `iceberg.benchmark` e `delta_lake.benchmark`.
- **Tabelas:** `region`, `nation`, `supplier`, `part`, `partsupp`, `customer`, `orders`, `lineitem`.
- **Queries:** Q1 a Q10 com cálculos analíticos agregados, filtros e joins multidimensionais.

### Fase 2 — Otimização e Data Skipping
Mede o benefício das técnicas de poda de partições (*partition pruning*):
- **Iceberg (`phase2_optimized`):**
  - `lineitem`: Particionamento oculto mensal `WITH (partitioning = ARRAY['month(shipdate)'])`.
  - `customer`: Particionamento por `mktsegment`.
- **Delta Lake (`phase2_optimized`):**
  - `customer`: Particionamento explícito `WITH (partitioned_by = ARRAY['mktsegment'])`.
- **Queries:** `Q3_partitioned_join`, `Q6_partitioned_filter`, `Q7_partitioned_join` e `Q19_unpartitioned_filter` (controle).

---

## 📊 Artefatos e Resultados Gerados

Ao término da execução, todos os artefatos são consolidados na pasta `benchmark_results/`:

1. **Mestre Consolidado (`benchmark_results/`):**
   - `benchmark_report.md`: Relatório comparativo mestre consolidando todas as suítes e scale factors.
   - `runs_all.csv` e `runs_all.json`: Base de dados completa de todas as iterações e métricas de nós.
   - 4 figuras científicas consolidadas em PNG:
     - `1_executive_overview.png`: Tempo total acumulado, média geométrica, speedup % e escalabilidade log-log.
     - `2_query_divergence.png`: Barras horizontais divergentes centradas em zero (% de vantagem por query) ordenadas por magnitude.
     - `3_distribution_and_scatter.png`: Boxplots em escala logarítmica e gráfico de dispersão com paridade y=x.
     - `4_infrastructure_and_stability.png`: I/O MinIO, latência de catálogo, CPU dos workers e estabilidade temporal (CV %).

2. **Subpastas por Suíte e Escala:**
   - `benchmark_results/tpch_sf1/` e `tpch_sf10/`: Relatórios individuais TPC-H, gráficos e CSV/JSON.
   - `benchmark_results/tpcds_sf1/` e `tpcds_sf10/`: Relatórios individuais TPC-DS, gráficos e CSV/JSON.
   - `benchmark_results/phase2_sf1/` e `phase2_sf10/`: Planos físicos textuais (`plans/`), `summary.md` e `speedup.png`.

---

## 🛠️ Solução de Problemas (Troubleshooting)

### 1. `Connection refused` na porta 30080
- **Causa:** O Trino Coordinator ainda não inicializou ou o IP no `.env` está incorreto.
- **Solução:** Verifique o IP em `.env` e confirme os pods no nó master:
  ```bash
  ssh ubuntu@<MASTER_IP> "kubectl get pods -n lakehouse"
  ```

### 2. Falha de autenticação ou criação no MinIO / S3
- **Causa:** Credenciais S3 ou bucket ausente.
- **Solução:** Acesse o console do MinIO em `http://<WORKER1_IP>:30901` e confirme a existência do bucket `warehouse`.
