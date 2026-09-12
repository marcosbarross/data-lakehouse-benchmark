# Orquestração Automatizada de Lakehouse com IaC & Benchmark de Formatos de Tabela (Iceberg vs Delta Lake)

<p align="center">
  <a href="README.pt-BR.md">🇧🇷 <b>Versão em Português</b></a> | 
  <a href="README.md">🇺🇸 <b>English Version</b></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/OpenTofu-1.6+-FFDA1A?style=for-the-badge&logo=opentofu&logoColor=black" alt="OpenTofu" />
  <img src="https://img.shields.io/badge/Magalu_Cloud-MGC-0086FF?style=for-the-badge&logo=icloud&logoColor=white" alt="Magalu Cloud" />
  <img src="https://img.shields.io/badge/Vagrant-2.4+-1563FF?style=for-the-badge&logo=vagrant&logoColor=white" alt="Vagrant" />
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

Este repositório fornece uma solução completa e reprodutível de **Infraestrutura como Código (IaC)** para implantação automatizada de uma arquitetura moderna de **Data Lakehouse** sobre um cluster **Kubernetes (K3s)** multi-nó.

O projeto inclui uma esteira científica de **benchmarks de desempenho** comparando os dois principais formatos modernos de tabela aberta: **Apache Iceberg** e **Delta Lake**, consultados via motor analítico distribuído **Trino** sobre armazenamento de objetos S3 compatível (**MinIO**), utilizando o padrão da indústria **TPC-H (Scale Factor 1 - SF1)**.

### 🌐 Ambientes Híbridos Suportados
O repositório suporta dois alvos de execução de forma totalmente transparente:
1. **Nuvem (Magalu Cloud via OpenTofu):** Topologia com **6 nós**, projetada para avaliação experimental de alto desempenho com isolamento físico rigoroso entre coordenação, I/O de armazenamento, catálogos de metadados e computação distribuída (3 nós worker Trino de 16 GB dedicados).
2. **Local (Vagrant + VirtualBox):** Topologia com **3 nós**, ideal para desenvolvimento offline e testes rápidos.

Desenvolvido no escopo de Trabalho de Conclusão de Curso (TCC) em Engenharia no **Instituto Federal de Pernambuco (IFPE) - Campus Paulista**.

---

## 🏗️ Arquitetura & Topologia do Cluster

A arquitetura desacopla rigidamente as camadas de **Coordenação**, **Armazenamento**, **Catálogo/Metadados** e **Computação Distribuída** no Kubernetes.

```mermaid
graph TD
    subgraph Management["Infraestrutura como Código & Cliente de Benchmark"]
        IaC["OpenTofu / Vagrant"]
        AnsibleEngine["Motor de Automação Ansible"]
        Bench["Suíte de Benchmark (Runner Python)"]
    end

    subgraph Cluster["Cluster Kubernetes K3s (namespace: lakehouse)"]
        subgraph MasterNode["k3s-master (Camada de Coordenação)"]
            K3sMaster["K3s Control Plane"]
            TrinoCoord["Trino Coordinator (:8080 -> :30080)"]
        end

        subgraph Worker1["k3s-worker1 (Armazenamento Dedicado)"]
            K3sAgent1["K3s Agent (node-role: storage)"]
            MinIO["MinIO S3 Storage (:30901 Console, :30900 API)"]
            TaintNotice["Taint: dedicated=minio:NoSchedule"]
        end

        subgraph Worker5["k3s-worker5 (Metadados Dedicados)"]
            K3sAgent5["K3s Agent (node-role: catalog)"]
            Postgres["PostgreSQL 16 (Iceberg JDBC Catalog)"]
            Hive["Hive Metastore 4.2 (Delta Lake Catalog)"]
            TaintCatalog["Taint: dedicated=catalog:NoSchedule"]
        end

        subgraph Worker2["k3s-worker2 (Computação 1 - 16 GB)"]
            K3sAgent2["K3s Agent (node-role: compute)"]
            TrinoW1["Trino Worker Pod 1 (12 GB JVM)"]
        end

        subgraph Worker3["k3s-worker3 (Computação 2 - 16 GB)"]
            K3sAgent3["K3s Agent (node-role: compute)"]
            TrinoW2["Trino Worker Pod 2 (12 GB JVM)"]
        end

        subgraph Worker4["k3s-worker4 (Computação 3 - 16 GB)"]
            K3sAgent4["K3s Agent (node-role: compute)"]
            TrinoW3["Trino Worker Pod 3 (12 GB JVM)"]
        end
    end

    IaC -->|Provisiona Instâncias, SG e SSH| Cluster
    AnsibleEngine -->|Bootstrap K3s, Labels, Taints e Manifestos| Cluster
    Bench -->|Executa Queries SQL TPC-H| TrinoCoord

    TrinoCoord -.->|Metadados Iceberg (JDBC)| Postgres
    TrinoCoord -.->|Metadados Delta Lake (Thrift)| Hive
    TrinoCoord -->|Distribui Planos de Execução| TrinoW1
    TrinoCoord -->|Distribui Planos de Execução| TrinoW2
    TrinoCoord -->|Distribui Planos de Execução| TrinoW3

    TrinoW1 -.->|Leitura Parquet S3| MinIO
    TrinoW2 -.->|Leitura Parquet S3| MinIO
    TrinoW3 -.->|Leitura Parquet S3| MinIO
```

### Topologia das Instâncias na Nuvem (Magalu Cloud - 6 Nós)

| Nó | Papel Arquitetural | Tipo de Máquina | vCPUs | RAM | Configuração / Isolamento |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`lakehouse-k3s-master`** | Control Plane & Trino Coordinator | `BV2-4-40` | 2 | 4 GB | `node-role.kubernetes.io/control-plane: true` |
| **`lakehouse-k3s-worker1`** | Armazenamento de Objetos S3 Dedicado | `BV4-8-100` | 4 | 8 GB | Label `node-role: storage`<br>Taint `dedicated=minio:NoSchedule` (100 GB NVMe) |
| **`lakehouse-k3s-worker5`** | Catálogos Dedicados (Postgres + Hive) | `BV2-4-40` | 2 | 4 GB | Label `node-role: catalog`<br>Taint `dedicated=catalog:NoSchedule` |
| **`lakehouse-k3s-worker2`** | Nó de Computação Trino 1 | `BV4-16-100` | 4 | 16 GB | Label `node-role: compute` (12 GB Heap JVM) |
| **`lakehouse-k3s-worker3`** | Nó de Computação Trino 2 | `BV4-16-100` | 4 | 16 GB | Label `node-role: compute` (12 GB Heap JVM) |
| **`lakehouse-k3s-worker4`** | Nó de Computação Trino 3 | `BV4-16-100` | 4 | 16 GB | Label `node-role: compute` (12 GB Heap JVM) |

> **Recursos Totais na Nuvem**: 20 vCPUs, 64 GB de memória RAM e 420 GB em disco SSD NVMe.


### Topologia Local de Desenvolvimento (Vagrant - 3 Nós)

| Nó | Função | IP Estático | vCPUs | RAM | Sistema Base |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`k3s-master`** | Control Plane & Trino Coordinator | `192.168.56.80` | 2 | 2 GB | Ubuntu 24.04 LTS |
| **`k3s-worker1`** | Armazenamento Dedicado (MinIO) | `192.168.56.81` | 2 | 8 GB | Ubuntu 24.04 LTS |
| **`k3s-worker2`** | Catálogos e Computação Trino | `192.168.56.82` | 2 | 4 GB | Ubuntu 24.04 LTS |

---

## ⚙️ Referência de Serviços & Portas

| Serviço | Componente | Ponto de Acesso / URL | Credenciais Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| **Trino** | Web UI / Coord. | `http://<IP_MASTER>:30080` | Usuário: `trino` | Motor SQL distribuído |
| **MinIO** | Console Web | `http://<IP_WORKER1>:30901` | Usuário: `admin`<br>Senha: `password123` | Dashboard gerencial do S3 |
| **MinIO** | S3 API Endpoint | `http://<IP_WORKER1>:30900` | Usuário: `admin`<br>Senha: `password123` | Endpoint da API S3 (`warehouse`) |
| **PostgreSQL** | Catálogo Iceberg | `http://<IP_MASTER>:30432` | Usuário: `admin`<br>Senha: `password123` | Banco `iceberg_catalog` |
| **Hive Metastore** | Catálogo Delta | `thrift://hive-metastore:9083` | *N/A (Interno ao cluster)* | Metastore Thrift para Delta Lake |
| **Kubernetes** | K3s API | `https://<IP_MASTER>:6443` | *Kubeconfig no Master* | Orquestrador de contêineres |

---

## 📊 Configuração dos Catálogos do Lakehouse

O Trino é configurado previamente com três catálogos:

1. **`tpch`**: Gerador oficial de dados sintéticos do TPC-H integrado ao Trino (fonte para Scale Factor 1, ~1GB).
2. **`iceberg`**:
   - Conector: `iceberg`
   - Metastore: `jdbc` conectado ao PostgreSQL (`iceberg_catalog`).
   - Armazenamento: MinIO (`s3://warehouse/`) com path-style access.
3. **`delta_lake`**:
   - Conector: `delta_lake`
   - Metastore: Apache Hive Metastore via protocolo Thrift.
   - Armazenamento: MinIO (`s3a://warehouse/`) com path-style access.

---

## 🚀 Como Executar na Nuvem (Magalu Cloud)

### 1. Pré-requisitos
- [OpenTofu](https://opentofu.org/) instalado (`tofu version >= 1.6`).
- Conta e **API Key** ativa na Magalu Cloud.
- Par de chaves SSH (`~/.ssh/xerlock` e `~/.ssh/xerlock.pub`).
- Python 3.10+ com virtualenv.

### 2. Configurar o Ambiente Virtual Python
```bash
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Provisionar a Infraestrutura com OpenTofu
```bash
cd tofu
cp terraform.tfvars.example terraform.tfvars
```
Edite o `terraform.tfvars` inserindo sua chave de API e caminhos da chave SSH:
```hcl
mgc_api_key         = "SUA_API_KEY_AQUI"
region              = "br-se1"
ssh_public_key_path = "~/.ssh/xerlock.pub"
ssh_private_key_path= "~/.ssh/xerlock"
```

Em seguida, inicialize e aplique:
```bash
tofu init
tofu apply
```
> **Automação Integrada:** O OpenTofu criará as 5 VMs na Magalu Cloud e gerará **automaticamente**:
> - O arquivo de inventário Ansible em `ansible/inventory/hosts.magalu.yml`.
> - O arquivo de variáveis de ambiente `.env` na raiz do projeto com o IP público do Trino e do MinIO.

Retorne à raiz do projeto:
```bash
cd ..
```

### 4. Executar o Provisionamento Ansible
Execute o playbook apontando para o inventário da Magalu Cloud:
```bash
ansible-playbook -i ansible/inventory/hosts.magalu.yml ansible/site.yml
```
O Ansible irá:
1. Instalar o K3s Master e conectar os 4 Workers.
2. Aplicar o label `node-role=storage` e o taint `dedicated=minio:NoSchedule` no nó `worker1`.
3. Aplicar o label `node-role=compute` nos nós `worker2`, `worker3` e `worker4`.
4. Implantar o MinIO, o PostgreSQL e o Hive Metastore.
5. Implantar o Trino Coordinator no nó Master e **3 réplicas do Trino Worker**, espalhadas automaticamente exatamente 1 por nó de computação via `podAntiAffinity`.

---

## 💻 Como Executar Localmente (Vagrant)

Caso queira rodar localmente no VirtualBox:

```bash
# 1. Ativar o virtualenv
source env/bin/activate

# 2. Subir o cluster local
vagrant up

# 3. Executar o playbook local (executado automaticamente pelo Vagrant ou reaplicável com:)
ansible-playbook -i ansible/inventory/hosts.yml ansible/site.yml
```

---

## 🧪 Executando a Suíte de Benchmarks

A suíte de benchmarks foi desenvolvida em Python e conecta-se automaticamente ao cluster Trino. O arquivo `.env` gerado pelo OpenTofu já direciona as consultas para o IP público correto do Trino Coordinator na Magalu Cloud.

### Ponto Único de Entrada

É possível executar todo o fluxo de testes ou suítes específicas através de uma única chamada em Python:

```bash
# 1. Execução padrão completa (TPC-H Fase 1 + Fase 2 + TPC-DS em SF1 e SF10, 3 iterações e auto-setup)
python run_benchmark.py

# 2. Executar grande escala SF100 sob demanda (apenas se especificado explicitamente)
python run_benchmark.py --scale-factor sf100

# 3. Executar suíte específica (ex: apenas TPC-DS em SF10)
python run_benchmark.py --benchmark tpcds --scale-factor sf10

# 4. Regerar o relatório consolidado e os 6 gráficos sem reexecutar queries
python run_benchmark.py --report-only
```

### Execução de Fases Isoladas do TPC-H

- **Fase 1: Baseline Geral (TPC-H SF1 — Q1 a Q10):**
  ```bash
  python run_benchmark.py --suite phase1
  ```
  Gera o relatório individual e gráficos comparativos em `benchmark_results/tpch_sf1/`.

- **Fase 2: Otimizações de Leitura e Data Skipping (Q3, Q6, Q7, Q19):**
  ```bash
  python run_benchmark.py --suite phase2
  ```
  Avalia particionamento temporal (*hidden partitioning*) e categórico com coleta profunda de métricas via `EXPLAIN ANALYZE`, salvando em `benchmark_results/phase2_sf1/`.

Para opções avançadas via CLI, consulte [benchmark/README.md](benchmark/README.md).


---

## 🛠️ Operação e Comandos Úteis

### Conectar via SSH nos Nós
```bash
# Master
ssh -i ~/.ssh/xerlock ubuntu@<IP_PUBLICO_MASTER>

# Inspecionar Pods e Nós no Master
kubectl get nodes -o wide
kubectl get pods -n lakehouse -o wide
```

### Acessar o CLI Interativo do Trino
```bash
ssh -i ~/.ssh/xerlock ubuntu@<IP_PUBLICO_MASTER> \
  "kubectl exec -it deploy/trino-coordinator -n lakehouse -- trino"
```
Dentro do CLI:
```sql
SHOW CATALOGS;
SELECT count(*) FROM iceberg.benchmark.lineitem;
SELECT count(*) FROM delta_lake.benchmark.lineitem;
```

### Encerrar Recursos na Nuvem
Para evitar custos desnecessários após o término dos testes:
```bash
cd tofu
tofu destroy
```

---

## 📁 Estrutura do Repositório

```text
.
├── tofu/                               # Módulo OpenTofu para provisionamento na Magalu Cloud
│   ├── vms.tf                          # Definição das 5 instâncias (Master, Storage, 3 Compute)
│   ├── security.tf                     # Grupos de segurança e regras de firewall
│   ├── inventory.tf                    # Geração automática de hosts.magalu.yml e .env
│   ├── variables.tf                    # Tipos de instância, região e chaves SSH
│   └── outputs.tf                      # Exibição de IPs públicos e privados
├── ansible/                            # Automação de configuração e orquestração do cluster
│   ├── site.yml                        # Playbook principal
│   ├── ansible.cfg                     # Configurações do Ansible
│   ├── inventory/
│   │   ├── hosts.yml                   # Inventário local para Vagrant
│   │   └── hosts.magalu.yml            # Inventário para Magalu Cloud (gerado pelo OpenTofu)
│   └── roles/
│       ├── k3s_install/                # Bootstrap K3s, labels de nós e isolamento com taints
│       ├── postgres/                   # Catálogo JDBC para Apache Iceberg
│       ├── minio/                      # Armazenamento S3 com nó dedicado e PV local
│       ├── hive_metastore/             # Metastore Apache Hive para Delta Lake
│       └── trino/                      # Trino Coordinator e 3 Workers distribuídos
├── benchmark/                          # Suíte unificada de benchmarks do lakehouse
│   ├── README.md                       # Guia abrangente dos benchmarks
│   ├── common/                         # Cliente Trino, retentativas DBAPI, parser e config
│   ├── phase1_baseline/                # Baseline geral TPC-H SF1 (Q1 a Q10)
│   └── phase2_optimization/            # Otimização, particionamento e data skipping
├── run_benchmark.py                    # Ponto único de entrada para rodar todos ou parte dos benchmarks
├── benchmark_phase2.py                 # Atalho de conveniência para a Fase 2
├── Vagrantfile                         # Topologia local multi-nó VirtualBox
├── requirements.txt                    # Dependências Python do projeto
├── README.md                           # English Documentation
└── README.pt-BR.md                     # Documentação em Português
```

---

## 🎓 Contexto Acadêmico

Este projeto é parte integrante do Trabalho de Conclusão de Curso (TCC) de **Marcos Barros** no curso de Engenharia do **Instituto Federal de Educação, Ciência e Tecnologia de Pernambuco (IFPE) - Campus Paulista**.

- **Título**: *Infraestrutura como Código para Orquestração Automatizada de um Ambiente Lakehouse em Kubernetes*
- **Orientador**: IFPE - Campus Paulista

---

## 📄 Licença

Distribuído sob a licença [MIT](LICENSE). Sinta-se livre para utilizar, modificar e expandir para fins acadêmicos e de pesquisa.
