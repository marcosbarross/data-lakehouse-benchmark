# Provisionamento do Cluster Lakehouse na Magalu Cloud (OpenTofu)

Este módulo OpenTofu automatiza o provisionamento das instâncias virtuais, grupos de segurança e chaves SSH na **Magalu Cloud (MGC)**, gerando automaticamente o inventário Ansible compatível com o cluster.

---

## 📋 Pré-requisitos

1. **OpenTofu** instalado (`tofu version >= 1.6`).
2. Conta na **Magalu Cloud** com uma **API Key** gerada.
3. Chave SSH local (gerada via `ssh-keygen -t rsa -b 4096` ou `ssh-keygen -t ed25519`).

---

## 🚀 Como Usar

### 1. Configurar as Variáveis

Copie o arquivo de exemplo `terraform.tfvars.example` para `terraform.tfvars`:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edite o arquivo `terraform.tfvars` preenchendo sua `mgc_api_key` e ajustando os caminhos da chave SSH se necessário:

```hcl
mgc_api_key         = "SUA_API_KEY_AQUI"
region              = "br-se1"
ssh_public_key_path = "~/.ssh/xerlock.pub"
ssh_private_key_path= "~/.ssh/xerlock"
```

### 2. Inicializar e Validar

```bash
tofu init
tofu validate
```

### 3. Planejar e Aplicar a Infraestrutura

```bash
tofu plan
tofu apply
```

Ao finalizar, o OpenTofu irá:
- Provisionar o Security Group com regras de firewall.
- Cadastrar sua chave SSH na Magalu Cloud.
- Criar as 6 instâncias virtuais (Topologia de Isolamento Estrito):
  - `lakehouse-k3s-master` (`BV2-4-40`: 2 vCPUs, 4 GB RAM - Control Plane & Trino Coordinator)
  - `lakehouse-k3s-worker1` (`BV4-8-40`: 4 vCPUs, 8 GB RAM - Storage Dedicado MinIO com Taint)
  - `lakehouse-k3s-worker5` (`BV2-4-40`: 2 vCPUs, 4 GB RAM - Catálogos Dedicados Postgres + Hive com Taint)
  - `lakehouse-k3s-worker2` (`BV4-16-100`: 4 vCPUs, 16 GB RAM - Trino Compute Worker 1)
  - `lakehouse-k3s-worker3` (`BV4-16-100`: 4 vCPUs, 16 GB RAM - Trino Compute Worker 2)
  - `lakehouse-k3s-worker4` (`BV4-16-100`: 4 vCPUs, 16 GB RAM - Trino Compute Worker 3)
- **Gerar automaticamente** o inventário Ansible em `../ansible/inventory/hosts.magalu.yml`.
- **Gerar automaticamente** o arquivo `.env` na raiz do projeto com o IP público do Trino para execução dos benchmarks.


### 4. Executar o Ansible Playbook

Com as máquinas criadas, execute o provisionamento do cluster K3s e dos serviços:

```bash
cd ..
ansible-playbook -i ansible/inventory/hosts.magalu.yml ansible/site.yml
```

---

## 🧹 Destruição dos Recursos

Para encerrar todas as instâncias e evitar custos adicionais após os benchmarks:

```bash
tofu destroy
```
