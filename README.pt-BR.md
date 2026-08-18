# Orquestração Automatizada de Lakehouse com IaC & Benchmark de Formatos de Tabela (Iceberg vs Delta Lake)

<p align="center">
  <a href="README.pt-BR.md">🇧🇷 <b>Versão em Português</b></a> | 
  <a href="README.md">🇺🇸 <b>English Version</b></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Vagrant-2.4+-1563FF?style=for-the-badge&logo=vagrant&logoColor=white" alt="Vagrant" />
  <img src="https://img.shields.io/badge/VirtualBox-7.0+-183A61?style=for-the-badge&logo=virtualbox&logoColor=white" alt="VirtualBox" />
  <img src="https://img.shields.io/badge/Kubernetes-K3s-FFC61C?style=for-the-badge&logo=k3s&logoColor=black" alt="K3s" />
  <img src="https://img.shields.io/badge/Ansible-2.16+-EE0000?style=for-the-badge&logo=ansible&logoColor=white" alt="Ansible" />
  <img src="https://img.shields.io/badge/Trino-483-DD00A1?style=for-the-badge&logo=trino&logoColor=white" alt="Trino" />
  <img src="https://img.shields.io/badge/Apache_Iceberg-Lakehouse-008080?style=for-the-badge&logo=apache&logoColor=white" alt="Apache Iceberg" />
  <img src="https://img.shields.io/badge/Delta_Lake-Storage-00ADD8?style=for-the-badge&logo=databricks&logoColor=white" alt="Delta Lake" />
  <img src="https://img.shields.io/badge/MinIO-S3_Storage-C72C48?style=for-the-badge&logo=minio&logoColor=white" alt="MinIO" />
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
</p>

---

## 📌 Visão Geral

Este repositório contém uma infraestrutura completa, automatizada e reproduzível como código (**Infrastructure as Code - IaC**) para implantação de uma arquitetura moderna de **Data Lakehouse** em um cluster **Kubernetes (K3s)** multi-nó.

O projeto inclui uma esteira automatizada de testes de desempenho (benchmark) comparando os dois principais formatos modernos de tabela: **Apache Iceberg** e **Delta Lake**, consultados pelo motor analítico **Trino** com cargas de trabalho padronizadas do **TPC-H (Fator de Escala 1 - SF1)**.

Desenvolvido no escopo de Trabalho de Conclusão de Curso (TCC) no Instituto Federal de Educação, Ciência e Tecnologia de Pernambuco (IFPE).

---

## 🏗️ Arquitetura & Topologia de Componentes

Toda a infraestrutura é provisionada utilizando **Vagrant (VirtualBox)** e configurada automaticamente via **Playbooks do Ansible** em uma rede privada dedicada (`192.168.56.0/24`).

```mermaid
graph TD
    subgraph Host["Máquina Host"]
        Vagrant["Vagrant CLI & Triggers"]
        Ansible["Motor Ansible Playbook"]
        Bench["Script Python Benchmark TPC-H"]
    end

    subgraph Cluster["Cluster Kubernetes K3s (namespace lakehouse)"]
        subgraph MasterNode["k3s-master (192.168.56.80)"]
            K3sMaster["K3s Server (Control Plane)"]
            TrinoCoord["Trino Coordinator (:8080 -> NodePort :30080)"]
        end

        subgraph Worker1["k3s-worker1 (192.168.56.81)"]
            K3sAgent1["K3s Agent (Nó de Armazenamento)"]
            MinIO["MinIO S3 Storage (Console :30901, API :30900)"]
            PostgreSQL["PostgreSQL 16 (Catálogo JDBC Iceberg :30432)"]
            HiveMetastore["Apache Hive Metastore 4.2 (Catálogo Delta Lake :9083)"]
        end

        subgraph Worker2["k3s-worker2 (192.168.56.82)"]
            K3sAgent2["K3s Agent (Nó de Computação)"]
            TrinoWorker["Trino Worker Pod"]
        end
    end

    Vagrant -->|Cria as VMs| MasterNode
    Vagrant -->|Cria as VMs| Worker1
    Vagrant -->|Cria as VMs| Worker2
    Ansible -->|Provisiona o Cluster e Manifestos K8s| Cluster
    Bench -->|Executa Consultas SQL TPC-H| TrinoCoord

    TrinoCoord -.->|Catálogo Iceberg (JDBC)| PostgreSQL
    TrinoCoord -.->|Catálogo Delta Lake (Thrift)| HiveMetastore
    TrinoCoord -.->|Consultas e Ingestão de Dados| MinIO
    TrinoWorker -.->|Processamento Distribuído| MinIO
```

### Topologia das Máquinas Virtuais

| Nome do Nó | Função | Endereço IP | vCPUs | Memória RAM | Sistema Operacional Base |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`k3s-master`** | Control Plane K3s & Trino Coordinator | `192.168.56.80` | 2 | 2048 MB (2 GB) | Ubuntu 24.04 LTS (Bento) |
| **`k3s-worker1`** | Worker K3s & Armazenamento (MinIO, Postgres, Hive) | `192.168.56.81` | 2 | 8192 MB (8 GB) | Ubuntu 24.04 LTS (Bento) |
| **`k3s-worker2`** | Worker K3s & Trino Worker (Computação) | `192.168.56.82` | 2 | 4096 MB (4 GB) | Ubuntu 24.04 LTS (Bento) |

> **Alocação Total de Recursos**: 6 vCPUs, ~14,3 GB de memória RAM.

---

## ⚙️ Referência de Tecnologias & Serviços

| Serviço | Tecnologia & Versão | Ponto de Acesso / URL | Credenciais Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **Motor de Consulta** | Trino `483` | `http://192.168.56.80:30080/ui` | Usuário: `trino` | Motor de consulta SQL distribuído |
| **Armazenamento de Objetos** | MinIO `latest` | `http://192.168.56.80:30901` (Console)<br>`http://192.168.56.80:30900` (API) | Usuário: `admin`<br>Senha: `password123` | Storage compatível com S3 (bucket `warehouse`) |
| **Catálogo de Metadados** | PostgreSQL `16-alpine` | `192.168.56.80:30432` | Usuário: `admin`<br>Senha: `password123`<br>Banco: `iceberg_catalog` | Catálogo JDBC para Apache Iceberg e backend do Hive |
| **Metastore Delta** | Apache Hive Metastore `4.2.0` | `thrift://hive-metastore.lakehouse.svc:9083` | *N/A (Acesso interno)* | Hive Metastore Standalone para Delta Lake |
| **Orquestração** | K3s `v1.31.4+k3s1` | `https://192.168.56.80:6443` | *Kubeconfig no Master* | Distribuição Kubernetes leve certificada pela CNCF |

---

## 📊 Configuração dos Catálogos do Lakehouse

O Trino é configurado previamente com três catálogos:

1. **`tpch`**: Gerador de dados sintéticos TPC-H integrado ao Trino, utilizado como fonte para a carga de benchmark (Fator de Escala 1, ~1GB).
2. **`iceberg`**:
   - Conector: `iceberg`
   - Tipo de Catálogo: `jdbc` (conectado ao PostgreSQL `iceberg_catalog`)
   - Armazenamento: MinIO (`s3://warehouse/`) via path-style access.
3. **`delta_lake`**:
   - Conector: `delta_lake`
   - Metastore: Apache Hive Metastore via URI Thrift.
   - Armazenamento: MinIO (`s3a://warehouse/`) via path-style access.

---

## 📋 Pré-requisitos

Antes de iniciar, certifique-se de possuir instalado no sistema hospedeiro (host):

- **Linux** (Ubuntu/Debian, Fedora, Arch, etc.) ou **macOS**
- [VirtualBox](https://www.virtualbox.org/) (Versão >= 7.0)
- [Vagrant](https://www.vagrantup.com/) (Versão >= 2.4)
- **Python 3.10+** com suporte a ambientes virtuais (`venv`)
- **Hardware Recomendado**: Mínimo de 16 GB de memória RAM e processador com 4+ núcleos físicos (6 vCPUs).

---

## 🚀 Guia de Instalação e Execução

### 1. Clonar o Repositório

```bash
git clone https://github.com/marcosbarross/data-lakehouse-benchmark.git
cd data-lakehouse-benchmark
```

### 2. Configurar o Ambiente Virtual Python

Crie e ative um ambiente virtual chamado `env` (o Vagrant está configurado para utilizar o binário do Ansible presente neste ambiente):

```bash
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Provisionar a Infraestrutura

Execute `vagrant up`. O comando irá:
1. Baixar a imagem base `bento/ubuntu-24.04`.
2. Criar e configurar as 3 máquinas virtuais com IPs estáticos e rede privada.
3. Acionar automaticamente o Ansible para instalar o K3s, configurar o cluster e implantar PostgreSQL, MinIO, Hive Metastore e Trino.

```bash
vagrant up
```

> ⏱️ *O processo de provisionamento inicial geralmente leva de 5 a 10 minutos, dependendo da velocidade da conexão de rede e do disco.*

### 4. Verificar o Status do Cluster

Verifique o estado das máquinas virtuais:
```bash
vagrant status
```

Acesse o nó master via SSH e verifique os pods implantados:
```bash
vagrant ssh k3s-master
kubectl get nodes -o wide
kubectl get pods -n lakehouse -o wide
exit
```

Todos os pods (`trino-coordinator`, `trino-worker`, `minio`, `postgres`, `hive-metastore`) devem estar em estado `Running`.

---

## 🧪 Executando o Benchmark TPC-H

O repositório inclui um script de benchmark automatizado em Python (`benchmark_tpch.py`) que realiza as seguintes etapas:

1. **Criação de Schemas**: Cria o schema `benchmark` nos catálogos `iceberg` e `delta_lake`.
2. **Ingestão e Carga dos Dados**: Copia as tabelas padrão do TPC-H SF1 (`customer`, `orders`, `lineitem`, `part`, `partsupp`, `supplier`, `nation`, `region`) a partir de `tpch.sf1` para os dois catálogos em formato Parquet no MinIO.
3. **Execução das Consultas**: Executa as queries analíticas `Q1` até `Q10` em ambos os formatos de tabela por 3 iterações consecutivas.
4. **Cálculo de Estatísticas**: Calcula média, tempo mínimo, tempo máximo, desvio padrão e speedup relativo.
5. **Geração de Gráficos**: Cria gráficos comparativos em alta resolução no diretório `benchmark_plots/`.
6. **Relatório em Markdown**: Compila os resultados detalhados no arquivo `benchmark_report.md`.

### Executar o Benchmark

Com o ambiente virtual ativado:

```bash
python benchmark_tpch.py
```

---

## 📈 Resumo dos Resultados do Benchmark

*Exemplo de execução do benchmark com TPC-H SF1 (~1GB) nas 10 consultas (3 iterações cada):*

| Query | Média Iceberg (s) | Média Delta Lake (s) | Speedup Relativo (Delta vs Iceberg) | Formato Vencedor |
| :---: | :---: | :---: | :---: | :---: |
| **Q1** | 0.67s | 0.60s | 1.13x | 🏆 Delta Lake |
| **Q2** | 0.59s | 0.65s | 0.91x | 🏆 Iceberg |
| **Q3** | 0.90s | 0.78s | 1.16x | 🏆 Delta Lake |
| **Q4** | 0.62s | 0.73s | 0.86x | 🏆 Iceberg |
| **Q5** | 1.11s | 1.15s | 0.97x | 🏆 Iceberg |
| **Q6** | 0.28s | 0.37s | 0.77x | 🏆 Iceberg |
| **Q7** | 0.99s | 1.07s | 0.93x | 🏆 Iceberg |
| **Q8** | 1.42s | 1.65s | 0.86x | 🏆 Iceberg |
| **Q9** | 1.62s | 1.69s | 0.96x | 🏆 Iceberg |
| **Q10** | 1.15s | 1.11s | 1.04x | 🏆 Delta Lake |
| **Tempo Total Acumulado** | **9.36s** | **9.79s** | **-** | 🏆 **Iceberg (4.3% mais rápido)** |

### Comparativos Visuais

| Tempo Médio por Query | Speedup Relativo | Tempo Total Acumulado |
| :---: | :---: | :---: |
| ![Iceberg vs Delta](benchmark_plots/iceberg_vs_deltalake.png) | ![Speedup](benchmark_plots/speedup_deltalake_vs_iceberg.png) | ![Tempo Total](benchmark_plots/total_time_comparison.png) |

---

## 🛠️ Comandos Úteis e Administração

### CLI Interativo do Trino
Acesse a linha de comando do Trino diretamente do cluster:
```bash
vagrant ssh k3s-master -c "kubectl exec -it deploy/trino-coordinator -n lakehouse -- trino"
```

Consultas úteis no CLI do Trino:
```sql
SHOW CATALOGS;
SHOW SCHEMAS FROM iceberg;
SHOW SCHEMAS FROM delta_lake;
SELECT count(*) FROM iceberg.benchmark.lineitem;
SELECT count(*) FROM delta_lake.benchmark.lineitem;
```

### Reexecução do Provisionamento Ansible
Caso você altere alguma role ou configuração do Ansible, reaplique sem destruir as VMs:
```bash
./env/bin/ansible-playbook -i ansible/inventory/hosts.yml ansible/site.yml
```

### Encerramento da Infraestrutura
Para suspender ou destruir as máquinas virtuais ao terminar:
```bash
# Suspender máquinas virtuais (salvar estado)
vagrant suspend

# Desligar máquinas virtuais
vagrant halt

# Destruir completamente e liberar espaço em disco
vagrant destroy -f
```

---

## 📁 Estrutura do Repositório

```text
.
├── Vagrantfile                         # Definição e topologia das VMs VirtualBox e provisionamento
├── requirements.txt                    # Dependências Python (Ansible, Trino DBAPI, Matplotlib, etc.)
├── benchmark_tpch.py                   # Ingestão TPC-H, execução do benchmark e geração de relatórios
├── benchmark_report.md                 # Relatório detalhado dos resultados do benchmark
├── benchmark_plots/                    # Gráficos de comparação de desempenho gerados
│   ├── iceberg_vs_deltalake.png
│   ├── speedup_deltalake_vs_iceberg.png
│   └── total_time_comparison.png
├── ansible/
│   ├── site.yml                        # Playbook principal do Ansible
│   ├── inventory/
│   │   └── hosts.yml                   # Inventário de nós, grupos e chaves SSH
│   └── roles/
│       ├── k3s_install/                # Instalação e configuração do K3s master e workers
│       ├── postgres/                   # Manifesto e configuração do catálogo PostgreSQL
│       ├── minio/                      # Manifesto e configuração do MinIO S3
│       ├── hive_metastore/             # Manifesto e serviço do Apache Hive Metastore
│       └── trino/                      # Manifestos do Trino Coordinator, Workers e Catálogos
├── utils/
│   └── README.MD                       # Referência rápida de endpoints e comandos
├── README.md                           # Documentação em Inglês
└── README.pt-BR.md                     # Documentação em Português
```

---

## 🎓 Contexto Acadêmico

Este projeto integra o Trabalho de Conclusão de Curso (TCC) de **Marcos Barros** no **Instituto Federal de Educação, Ciência e Tecnologia de Pernambuco (IFPE)**.

- **Título**: *Infraestrutura como Código para Orquestração Automatizada de um Ambiente Lakehouse em Kubernetes*
- **Instituição**: IFPE - Campus Pesqueira

---

## 📄 Licença

Este projeto é disponibilizado sob a licença [MIT](LICENSE) - livre para uso, modificação e distribuição para fins acadêmicos, profissionais e de pesquisa.
