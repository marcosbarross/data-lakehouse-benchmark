locals {
  master_public_ip   = try(coalesce(mgc_virtual_machine_instances.master.ipv4, mgc_virtual_machine_instances.master.network_interfaces[0].ipv4, mgc_virtual_machine_instances.master.local_ipv4, mgc_virtual_machine_instances.master.network_interfaces[0].local_ipv4), "")
  worker1_public_ip  = try(coalesce(mgc_virtual_machine_instances.worker1.ipv4, mgc_virtual_machine_instances.worker1.network_interfaces[0].ipv4, mgc_virtual_machine_instances.worker1.local_ipv4, mgc_virtual_machine_instances.worker1.network_interfaces[0].local_ipv4), "")
  worker2_public_ip  = try(coalesce(mgc_virtual_machine_instances.worker2.ipv4, mgc_virtual_machine_instances.worker2.network_interfaces[0].ipv4, mgc_virtual_machine_instances.worker2.local_ipv4, mgc_virtual_machine_instances.worker2.network_interfaces[0].local_ipv4), "")
  worker3_public_ip  = try(coalesce(mgc_virtual_machine_instances.worker3.ipv4, mgc_virtual_machine_instances.worker3.network_interfaces[0].ipv4, mgc_virtual_machine_instances.worker3.local_ipv4, mgc_virtual_machine_instances.worker3.network_interfaces[0].local_ipv4), "")
  worker4_public_ip  = try(coalesce(mgc_virtual_machine_instances.worker4.ipv4, mgc_virtual_machine_instances.worker4.network_interfaces[0].ipv4, mgc_virtual_machine_instances.worker4.local_ipv4, mgc_virtual_machine_instances.worker4.network_interfaces[0].local_ipv4), "")
  worker5_public_ip  = try(coalesce(mgc_virtual_machine_instances.worker5.ipv4, mgc_virtual_machine_instances.worker5.network_interfaces[0].ipv4, mgc_virtual_machine_instances.worker5.local_ipv4, mgc_virtual_machine_instances.worker5.network_interfaces[0].local_ipv4), "")

  master_private_ip  = try(coalesce(mgc_virtual_machine_instances.master.local_ipv4, mgc_virtual_machine_instances.master.network_interfaces[0].local_ipv4, local.master_public_ip), "")
  worker1_private_ip = try(coalesce(mgc_virtual_machine_instances.worker1.local_ipv4, mgc_virtual_machine_instances.worker1.network_interfaces[0].local_ipv4, local.worker1_public_ip), "")
  worker2_private_ip = try(coalesce(mgc_virtual_machine_instances.worker2.local_ipv4, mgc_virtual_machine_instances.worker2.network_interfaces[0].local_ipv4, local.worker2_public_ip), "")
  worker3_private_ip = try(coalesce(mgc_virtual_machine_instances.worker3.local_ipv4, mgc_virtual_machine_instances.worker3.network_interfaces[0].local_ipv4, local.worker3_public_ip), "")
  worker4_private_ip = try(coalesce(mgc_virtual_machine_instances.worker4.local_ipv4, mgc_virtual_machine_instances.worker4.network_interfaces[0].local_ipv4, local.worker4_public_ip), "")
  worker5_private_ip = try(coalesce(mgc_virtual_machine_instances.worker5.local_ipv4, mgc_virtual_machine_instances.worker5.network_interfaces[0].local_ipv4, local.worker5_public_ip), "")
}

resource "local_file" "ansible_inventory_magalu" {
  filename        = "${path.module}/../ansible/inventory/hosts.magalu.yml"
  file_permission = "0644"
  content         = <<-EOT
all:
  vars:
    ansible_user: ${var.ssh_user}
    ansible_python_interpreter: /usr/bin/python3
    ansible_ssh_private_key_file: "${var.ssh_private_key_path}"
    ansible_ssh_common_args: "-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    extra_server_args: "--node-ip={{ internal_ip | default(ansible_host) }} --flannel-iface=ens3"
    extra_agent_args: "--node-ip={{ internal_ip | default(ansible_host) }} --flannel-iface=ens3"

  children:
    master:
      hosts:
        k3s-master:
          ansible_host: ${local.master_public_ip}
          internal_ip: ${local.master_private_ip}

    workers:
      hosts:
        k3s-worker1:
          ansible_host: ${local.worker1_public_ip}
          internal_ip: ${local.worker1_private_ip}
        k3s-worker2:
          ansible_host: ${local.worker2_public_ip}
          internal_ip: ${local.worker2_private_ip}
        k3s-worker3:
          ansible_host: ${local.worker3_public_ip}
          internal_ip: ${local.worker3_private_ip}
        k3s-worker4:
          ansible_host: ${local.worker4_public_ip}
          internal_ip: ${local.worker4_private_ip}
        k3s-worker5:
          ansible_host: ${local.worker5_public_ip}
          internal_ip: ${local.worker5_private_ip}

    k3s_cluster:
      children:
        master:
        workers:

    minio_node:
      hosts:
        k3s-worker1:

    catalog_nodes:
      hosts:
        k3s-worker5:

    compute_nodes:
      hosts:
        k3s-worker2:
        k3s-worker3:
        k3s-worker4:
EOT
}


resource "local_file" "benchmark_env" {
  filename        = "${path.module}/../.env"
  file_permission = "0644"
  content         = <<-EOT
# Gerado automaticamente pelo OpenTofu
TRINO_HOST=${local.master_public_ip}
TRINO_PORT=30080
TRINO_USER=trino
MINIO_ENDPOINT=http://${local.worker1_public_ip}:30900
MINIO_CONSOLE=http://${local.worker1_public_ip}:30901
BENCHMARK_SOURCE_CATALOG=tpch
BENCHMARK_SOURCE_SCHEMA=sf1
MINIO_BUCKET=warehouse
DELTA_STORAGE_SCHEME=s3a
BENCHMARK_ITERATIONS=3
EOT
}
