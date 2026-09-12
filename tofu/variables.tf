variable "mgc_api_key" {
  description = "Chave de API (API Key) para autenticação na Magalu Cloud"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "Região da Magalu Cloud para provisionamento (ex: br-se1, br-ne1)"
  type        = string
  default     = "br-se1"
}

variable "cluster_prefix" {
  description = "Prefixo aplicado ao nome dos recursos provisionados"
  type        = string
  default     = "lakehouse"
}

variable "image_name" {
  description = "Nome da imagem de sistema operacional para as instâncias"
  type        = string
  default     = "cloud-ubuntu-24.04 LTS"
}

variable "ssh_key_name" {
  description = "Nome do recurso de chave SSH na Magalu Cloud"
  type        = string
  default     = "lakehouse-bench-key"
}

variable "ssh_public_key" {
  description = "Conteúdo da chave pública SSH. Se vazio, lê do arquivo em ssh_public_key_path"
  type        = string
  default     = ""
}

variable "ssh_public_key_path" {
  description = "Caminho do arquivo de chave pública SSH caso ssh_public_key esteja vazio"
  type        = string
  default     = "~/.ssh/xerlock.pub"
}

variable "ssh_private_key_path" {
  description = "Caminho da chave privada SSH para ser configurada no inventário Ansible"
  type        = string
  default     = "~/.ssh/xerlock"
}

variable "ssh_user" {
  description = "Usuário padrão para conexões SSH nas instâncias"
  type        = string
  default     = "ubuntu"
}

variable "master_machine_type" {
  description = "Tipo de máquina para o nó Master / Trino Coordinator (2 vCPUs, 4 GB RAM)"
  type        = string
  default     = "BV2-4-40"
}

variable "worker1_machine_type" {
  description = "Tipo de máquina para o nó Worker 1 / MinIO Storage dedicado (4 vCPUs, 8 GB RAM, 100 GB NVMe)"
  type        = string
  default     = "BV4-8-100"
}

variable "worker2_machine_type" {
  description = "Tipo de máquina para o nó Worker 2 / Trino Compute Worker 1 (4 vCPUs, 16 GB RAM)"
  type        = string
  default     = "BV4-16-100"
}

variable "worker3_machine_type" {
  description = "Tipo de máquina para o nó Worker 3 / Trino Compute Worker 2 (4 vCPUs, 16 GB RAM)"
  type        = string
  default     = "BV4-16-100"
}

variable "worker4_machine_type" {
  description = "Tipo de máquina para o nó Worker 4 / Trino Compute Worker 3 (4 vCPUs, 16 GB RAM)"
  type        = string
  default     = "BV4-16-100"
}

variable "worker5_machine_type" {
  description = "Tipo de máquina para o nó Worker 5 / Catálogos Dedicados - Postgres + Hive (2 vCPUs, 4 GB RAM)"
  type        = string
  default     = "BV2-4-40"
}


variable "allowed_admin_cidr" {
  description = "CIDR autorizado para acessar SSH, API do K3s e NodePorts de gerenciamento"
  type        = string
  default     = "0.0.0.0/0"
}

variable "allocate_public_ipv4" {
  description = "Define se as instâncias virtuais devem receber um endereço IPv4 público"
  type        = bool
  default     = true
}
