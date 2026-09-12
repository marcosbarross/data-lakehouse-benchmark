# Automated Lakehouse Orchestration with IaC & Table Format Benchmark (Iceberg vs Delta Lake)

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

## 📌 Overview

This repository provides an automated, reproducible **Infrastructure as Code (IaC)** environment for deploying a modern **Data Lakehouse** architecture on top of a multi-node **Kubernetes (K3s)** cluster.

It includes an end-to-end performance benchmarking pipeline comparing the two leading modern open table formats: **Apache Iceberg** and **Delta Lake**, queried by the distributed SQL query engine **Trino** against standardized **TPC-H (Scale Factor 1 - SF1)** workloads backed by S3-compatible object storage (**MinIO**).

### 🌐 Dual Execution Environments Supported
The architecture is designed to support two deployment targets seamlessly:
1. **Cloud Production/Benchmark (Magalu Cloud via OpenTofu):** A **6-node** cluster engineered for high-performance scientific evaluation with strict physical isolation between coordination, storage I/O, metadata catalogs, and distributed compute workers (3 dedicated 16 GB Trino worker nodes).
2. **Local Development (Vagrant + VirtualBox):** A compact multi-node cluster (1 Master, 2 Workers) designed for offline testing and development workflows without cloud costs.

Developed as a Bachelor's Dissertation (TCC - *Trabalho de Conclusão de Curso*) project in Engineering at the **Federal Institute of Pernambuco (IFPE) - Campus Paulista**.

---

## 🏗️ Architecture & Topology

The architecture decouples the **Storage**, **Catalog/Metadata**, and **Distributed Compute** layers into dedicated Kubernetes nodes:

```mermaid
graph TD
    subgraph Management["Infrastructure as Code & Benchmark Client"]
        IaC["OpenTofu / Vagrant"]
        AnsibleEngine["Ansible Automation Engine"]
        Bench["Benchmark Suite (Python Runner)"]
    end

    subgraph Cluster["K3s Kubernetes Cluster (lakehouse namespace)"]
        subgraph MasterNode["k3s-master (Coordination Layer)"]
            K3sMaster["K3s Control Plane"]
            TrinoCoord["Trino Coordinator (:8080 -> :30080)"]
        end

        subgraph Worker1["k3s-worker1 (Dedicated Storage Layer)"]
            K3sAgent1["K3s Agent (node-role: storage)"]
            MinIO["MinIO S3 Storage (:30901 Console, :30900 API)"]
            TaintNotice["Taint: dedicated=minio:NoSchedule"]
        end

        subgraph Worker5["k3s-worker5 (Dedicated Metadata Layer)"]
            K3sAgent5["K3s Agent (node-role: catalog)"]
            Postgres["PostgreSQL 16 (Iceberg JDBC Catalog)"]
            Hive["Hive Metastore 4.2 (Delta Lake Catalog)"]
            TaintCatalog["Taint: dedicated=catalog:NoSchedule"]
        end

        subgraph Worker2["k3s-worker2 (Compute 1 - 16 GB)"]
            K3sAgent2["K3s Agent (node-role: compute)"]
            TrinoW1["Trino Worker Pod 1 (12 GB JVM)"]
        end

        subgraph Worker3["k3s-worker3 (Compute 2 - 16 GB)"]
            K3sAgent3["K3s Agent (node-role: compute)"]
            TrinoW2["Trino Worker Pod 2 (12 GB JVM)"]
        end

        subgraph Worker4["k3s-worker4 (Compute 3 - 16 GB)"]
            K3sAgent4["K3s Agent (node-role: compute)"]
            TrinoW3["Trino Worker Pod 3 (12 GB JVM)"]
        end
    end

    IaC -->|Provisions VMs, SG & SSH| Cluster
    AnsibleEngine -->|Bootstraps K3s, Labels, Taints & Manifests| Cluster
    Bench -->|Executes TPC-H SQL Queries| TrinoCoord

    TrinoCoord -.->|Iceberg Metadata (JDBC)| Postgres
    TrinoCoord -.->|Delta Lake Metadata (Thrift)| Hive
    TrinoCoord -->|Distributes Execution Plan| TrinoW1
    TrinoCoord -->|Distributes Execution Plan| TrinoW2
    TrinoCoord -->|Distributes Execution Plan| TrinoW3

    TrinoW1 -.->|Parquet Read over S3| MinIO
    TrinoW2 -.->|Parquet Read over S3| MinIO
    TrinoW3 -.->|Parquet Read over S3| MinIO
```

### Cloud Virtual Machine Topology (Magalu Cloud - 6 Nodes)

| Node | Architectural Role | Machine Type | vCPUs | RAM | Configuration / Isolation |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`lakehouse-k3s-master`** | Control Plane & Trino Coordinator | `BV2-4-40` | 2 | 4 GB | `node-role.kubernetes.io/control-plane: true` |
| **`lakehouse-k3s-worker1`** | Dedicated MinIO Object Storage | `BV4-8-100` | 4 | 8 GB | Label `node-role: storage`<br>Taint `dedicated=minio:NoSchedule` (100 GB NVMe) |
| **`lakehouse-k3s-worker5`** | Dedicated Metadata Catalogs (Postgres + Hive) | `BV2-4-40` | 2 | 4 GB | Label `node-role: catalog`<br>Taint `dedicated=catalog:NoSchedule` |
| **`lakehouse-k3s-worker2`** | Trino Compute Worker 1 | `BV4-16-100` | 4 | 16 GB | Label `node-role: compute` (12 GB JVM Heap) |
| **`lakehouse-k3s-worker3`** | Trino Compute Worker 2 | `BV4-16-100` | 4 | 16 GB | Label `node-role: compute` (12 GB JVM Heap) |
| **`lakehouse-k3s-worker4`** | Trino Compute Worker 3 | `BV4-16-100` | 4 | 16 GB | Label `node-role: compute` (12 GB JVM Heap) |

> **Total Cloud Resources**: 20 vCPUs, 64 GB RAM, 420 GB NVMe SSD storage.

### Local Virtual Machine Topology (Vagrant - 3 Nodes)

| Node | Role | Static IP | vCPUs | RAM | Base OS |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`k3s-master`** | Control Plane & Trino Coordinator | `192.168.56.80` | 2 | 2 GB | Ubuntu 24.04 LTS |
| **`k3s-worker1`** | Dedicated MinIO Storage | `192.168.56.81` | 2 | 8 GB | Ubuntu 24.04 LTS |
| **`k3s-worker2`** | Catalogs and Trino Worker Compute | `192.168.56.82` | 2 | 4 GB | Ubuntu 24.04 LTS |

---

## ⚙️ Stack & Services Reference

| Service | Component | Access Point / URL | Default Credentials | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Trino** | Web UI / Coord. | `http://<MASTER_IP>:30080` | User: `trino` | Distributed SQL query engine |
| **MinIO** | Web Console | `http://<WORKER1_IP>:30901` | User: `admin`<br>Pass: `password123` | S3 Management dashboard |
| **MinIO** | S3 API Endpoint | `http://<WORKER1_IP>:30900` | User: `admin`<br>Pass: `password123` | S3 API endpoint (`warehouse` bucket) |
| **PostgreSQL** | Iceberg Catalog | `http://<MASTER_IP>:30432` | User: `admin`<br>Pass: `password123` | Database `iceberg_catalog` |
| **Hive Metastore** | Delta Metastore | `thrift://hive-metastore:9083` | *N/A (Internal)* | Standalone Hive Metastore for Delta Lake |
| **Kubernetes** | K3s API | `https://<MASTER_IP>:6443` | *Kubeconfig on Master* | Lightweight certified Kubernetes distribution |

---

## 📊 Lakehouse Catalogs Configuration

Trino is pre-configured with three catalogs:

1. **`tpch`**: Built-in synthetic TPC-H data generator used as the source benchmark dataset (Scale Factor 1, ~1GB).
2. **`iceberg`**:
   - Connector: `iceberg`
   - Catalog Type: `jdbc` (backed by PostgreSQL `iceberg_catalog`)
   - Data Storage: MinIO (`s3://warehouse/`) via path-style access.
3. **`delta_lake`**:
   - Connector: `delta_lake`
   - Metastore: Apache Hive Metastore via Thrift URI.
   - Data Storage: MinIO (`s3a://warehouse/`) via path-style access.

---

## 🚀 Cloud Deployment Guide (Magalu Cloud)

### 1. Prerequisites
- [OpenTofu](https://opentofu.org/) installed (`tofu version >= 1.6`).
- Active **Magalu Cloud** account with an **API Key**.
- SSH key pair (`~/.ssh/xerlock` and `~/.ssh/xerlock.pub`).
- Python 3.10+ with `venv`.

### 2. Set Up Python Virtual Environment
```bash
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Provision Infrastructure with OpenTofu
```bash
cd tofu
cp terraform.tfvars.example terraform.tfvars
```
Edit `terraform.tfvars` with your API Key and SSH paths:
```hcl
mgc_api_key         = "YOUR_API_KEY_HERE"
region              = "br-se1"
ssh_public_key_path = "~/.ssh/xerlock.pub"
ssh_private_key_path= "~/.ssh/xerlock"
```

Initialize and apply:
```bash
tofu init
tofu apply
```
> **Seamless Automation:** OpenTofu provisions the 5 VMs and **automatically generates**:
> - The Ansible inventory at `ansible/inventory/hosts.magalu.yml`.
> - The `.env` environment variables file at the project root with public IP addresses for Trino and MinIO.

Return to the repository root:
```bash
cd ..
```

### 4. Run Ansible Provisioning
Execute the Ansible playbook using the generated inventory:
```bash
ansible-playbook -i ansible/inventory/hosts.magalu.yml ansible/site.yml
```
Ansible will:
1. Install K3s server on the Master and connect all 4 Workers.
2. Apply the label `node-role=storage` and taint `dedicated=minio:NoSchedule` on `worker1`.
3. Apply the label `node-role=compute` on `worker2`, `worker3`, and `worker4`.
4. Deploy MinIO, PostgreSQL, and Hive Metastore.
5. Deploy Trino Coordinator on the Master and **3 replicas of Trino Worker**, automatically distributed exactly 1 per compute node via `podAntiAffinity`.

---

## 💻 Local Deployment Guide (Vagrant)

To deploy locally on VirtualBox:

```bash
# 1. Activate virtual environment
source env/bin/activate

# 2. Spin up local cluster
vagrant up

# 3. Reapply Ansible playbook if needed
ansible-playbook -i ansible/inventory/hosts.yml ansible/site.yml
```

---

## 🧪 Running the Lakehouse Benchmark Suite

The benchmarking suite automatically reads connection configurations from the `.env` file generated by OpenTofu (or defaults to local Vagrant if `.env` is absent).

### Single Entrypoint Execution

You can run the entire benchmark pipeline or specific benchmark families with a single Python command:

```bash
# 1. Default unified execution (TPC-H Phase 1 & 2 + TPC-DS across SF1 and SF10, 3 iterations and auto-setup)
python run_benchmark.py

# 2. Run large scale factor SF100 on demand (executed only when explicitly passed)
python run_benchmark.py --scale-factor sf100

# 3. Run a specific benchmark suite (e.g., TPC-DS on SF10)
python run_benchmark.py --benchmark tpcds --scale-factor sf10

# 4. Regenerate master consolidated report and 6 chart categories from saved runs
python run_benchmark.py --report-only
```

### Running Individual Benchmark Phases

- **Phase 1: General Baseline (TPC-H SF1 — Q1 to Q10):**
  ```bash
  python run_benchmark.py --suite phase1
  ```
  Generates individual reports and comparison plots in `benchmark_results/tpch_sf1/`.

- **Phase 2: Read Optimization & Data Skipping (Q3, Q6, Q7, Q19):**
  ```bash
  python run_benchmark.py --suite phase2
  ```
  Evaluates temporal (*hidden partitioning*) and categorical partitioning against unpartitioned baselines with `EXPLAIN ANALYZE` metrics stored in `benchmark_results/phase2_sf1/`.

See [benchmark/README.md](benchmark/README.md) for full CLI parameters and metric details.


---

## 🛠️ Management & Useful Commands

### SSH into Cluster Nodes
```bash
# Connect to Master
ssh -i ~/.ssh/xerlock ubuntu@<MASTER_PUBLIC_IP>

# Inspect cluster state
kubectl get nodes -o wide
kubectl get pods -n lakehouse -o wide
```

### Access Trino CLI
```bash
ssh -i ~/.ssh/xerlock ubuntu@<MASTER_PUBLIC_IP> \
  "kubectl exec -it deploy/trino-coordinator -n lakehouse -- trino"
```
Inside Trino CLI:
```sql
SHOW CATALOGS;
SELECT count(*) FROM iceberg.benchmark.lineitem;
SELECT count(*) FROM delta_lake.benchmark.lineitem;
```

### Destroy Cloud Resources
To stop instances and avoid unnecessary cloud costs after testing:
```bash
cd tofu
tofu destroy
```

---

## 📁 Repository Structure

```text
.
├── tofu/                               # OpenTofu module for Magalu Cloud infrastructure
│   ├── vms.tf                          # VM definitions (Master, Storage, 3 Compute)
│   ├── security.tf                     # Firewall and Security Group rules
│   ├── inventory.tf                    # Automatic generation of hosts.magalu.yml and .env
│   ├── variables.tf                    # Instance machine types, region, and SSH keys
│   └── outputs.tf                      # Public and private IP output definitions
├── ansible/                            # Automated cluster configuration and service orchestration
│   ├── site.yml                        # Main playbook entrypoint
│   ├── ansible.cfg                     # Ansible core settings
│   ├── inventory/
│   │   ├── hosts.yml                   # Local inventory for Vagrant
│   │   └── hosts.magalu.yml            # Cloud inventory (generated by OpenTofu)
│   └── roles/
│       ├── k3s_install/                # K3s installation, node roles, labels and taints
│       ├── postgres/                   # JDBC Catalog for Apache Iceberg
│       ├── minio/                      # S3 Storage with dedicated node and hostPath PV
│       ├── hive_metastore/             # Apache Hive Metastore for Delta Lake
│       └── trino/                      # Trino Coordinator and 3 distributed Workers
├── benchmark/                          # Unified lakehouse benchmark suite
│   ├── README.md                       # Comprehensive benchmark documentation
│   ├── common/                         # Trino client, DBAPI retries, EXPLAIN parser, config
│   ├── phase1_baseline/                # TPC-H SF1 general baseline (Q1 to Q10)
│   └── phase2_optimization/            # Partitioning, read optimization and data skipping
├── run_benchmark.py                    # Single entrypoint script to run all or selected benchmarks
├── benchmark_phase2.py                 # Convenience wrapper for Phase 2 benchmark
├── Vagrantfile                         # Local multi-node VirtualBox topology definition
├── requirements.txt                    # Python dependencies
├── README.md                           # English Documentation
└── README.pt-BR.md                     # Documentação em Português
```

---

## 🎓 Academic Context

This project is part of the final undergraduate dissertation (TCC - *Trabalho de Conclusão de Curso*) by **Marcos Barros** at **Instituto Federal de Pernambuco (IFPE) - Campus Paulista**.

- **Title**: *Infraestrutura como Código para Orquestração Automatizada de um Ambiente Lakehouse em Kubernetes*
- **Institution**: IFPE - Campus Paulista

---

## 📄 License

Distributed under the [MIT License](LICENSE).
