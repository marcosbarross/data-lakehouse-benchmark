locals {
  ssh_pub_key = var.ssh_public_key != "" ? var.ssh_public_key : file(pathexpand(var.ssh_public_key_path))
  
  cloud_init_user_data = <<-EOF
    #cloud-config
    package_update: true
    packages:
      - python3
      - python3-pip
      - curl
      - nfs-common
      - avahi-daemon
      - libnss-mdns
  EOF
}

resource "mgc_ssh_keys" "cluster_key" {
  name = var.ssh_key_name
  key  = trimspace(local.ssh_pub_key)
}

# --- Nó Master / Trino Coordinator ---
resource "mgc_virtual_machine_instances" "master" {
  name                     = "${var.cluster_prefix}-k3s-master"
  machine_type             = var.master_machine_type
  image                    = var.image_name
  ssh_key_name             = mgc_ssh_keys.cluster_key.name
  creation_security_groups = [mgc_network_security_groups.cluster_sg.id]
  user_data                = base64encode(local.cloud_init_user_data)
  allocate_public_ipv4     = var.allocate_public_ipv4
}

# --- Nó Worker 1 / MinIO Storage Dedicado ---
resource "mgc_virtual_machine_instances" "worker1" {
  name                     = "${var.cluster_prefix}-k3s-worker1"
  machine_type             = var.worker1_machine_type
  image                    = var.image_name
  ssh_key_name             = mgc_ssh_keys.cluster_key.name
  creation_security_groups = [mgc_network_security_groups.cluster_sg.id]
  user_data                = base64encode(local.cloud_init_user_data)
  allocate_public_ipv4     = var.allocate_public_ipv4
}

# --- Nó Worker 2 / Trino Compute Worker 1 ---
resource "mgc_virtual_machine_instances" "worker2" {
  name                     = "${var.cluster_prefix}-k3s-worker2"
  machine_type             = var.worker2_machine_type
  image                    = var.image_name
  ssh_key_name             = mgc_ssh_keys.cluster_key.name
  creation_security_groups = [mgc_network_security_groups.cluster_sg.id]
  user_data                = base64encode(local.cloud_init_user_data)
  allocate_public_ipv4     = var.allocate_public_ipv4
}

# --- Nó Worker 3 / Trino Compute Worker 2 ---
resource "mgc_virtual_machine_instances" "worker3" {
  name                     = "${var.cluster_prefix}-k3s-worker3"
  machine_type             = var.worker3_machine_type
  image                    = var.image_name
  ssh_key_name             = mgc_ssh_keys.cluster_key.name
  creation_security_groups = [mgc_network_security_groups.cluster_sg.id]
  user_data                = base64encode(local.cloud_init_user_data)
  allocate_public_ipv4     = var.allocate_public_ipv4
}

# --- Nó Worker 4 / Trino Compute Worker 3 ---
resource "mgc_virtual_machine_instances" "worker4" {
  name                     = "${var.cluster_prefix}-k3s-worker4"
  machine_type             = var.worker4_machine_type
  image                    = var.image_name
  ssh_key_name             = mgc_ssh_keys.cluster_key.name
  creation_security_groups = [mgc_network_security_groups.cluster_sg.id]
  user_data                = base64encode(local.cloud_init_user_data)
  allocate_public_ipv4     = var.allocate_public_ipv4
}

# --- Nó Worker 5 / Catálogos de Metadados Dedicados (Postgres + Hive) ---
resource "mgc_virtual_machine_instances" "worker5" {
  name                     = "${var.cluster_prefix}-k3s-worker5"
  machine_type             = var.worker5_machine_type
  image                    = var.image_name
  ssh_key_name             = mgc_ssh_keys.cluster_key.name
  creation_security_groups = [mgc_network_security_groups.cluster_sg.id]
  user_data                = base64encode(local.cloud_init_user_data)
  allocate_public_ipv4     = var.allocate_public_ipv4
}

