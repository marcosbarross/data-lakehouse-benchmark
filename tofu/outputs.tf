output "master_public_ip" {
  description = "IP Publico do nó Master (Trino Coordinator / K3s Control Plane)"
  value       = local.master_public_ip
}

output "worker1_public_ip" {
  description = "IP Publico do nó Worker 1 (MinIO Storage Dedicado)"
  value       = local.worker1_public_ip
}

output "worker2_public_ip" {
  description = "IP Publico do nó Worker 2 (Trino Compute Worker 1)"
  value       = local.worker2_public_ip
}

output "worker3_public_ip" {
  description = "IP Publico do nó Worker 3 (Trino Compute Worker 2)"
  value       = local.worker3_public_ip
}

output "worker4_public_ip" {
  description = "IP Publico do nó Worker 4 (Trino Compute Worker 3)"
  value       = local.worker4_public_ip
}

output "worker5_public_ip" {
  description = "IP Publico do nó Worker 5 (Catálogos de Metadados Dedicados)"
  value       = local.worker5_public_ip
}

output "master_private_ip" {
  description = "IP Privado do nó Master"
  value       = local.master_private_ip
}

output "worker1_private_ip" {
  description = "IP Privado do nó Worker 1"
  value       = local.worker1_private_ip
}

output "worker2_private_ip" {
  description = "IP Privado do nó Worker 2"
  value       = local.worker2_private_ip
}

output "worker3_private_ip" {
  description = "IP Privado do nó Worker 3"
  value       = local.worker3_private_ip
}

output "worker4_private_ip" {
  description = "IP Privado do nó Worker 4"
  value       = local.worker4_private_ip
}

output "worker5_private_ip" {
  description = "IP Privado do nó Worker 5"
  value       = local.worker5_private_ip
}


output "trino_ui_url" {
  description = "URL de acesso a interface web do Trino"
  value       = "http://${local.master_public_ip}:30080"
}

output "minio_console_url" {
  description = "URL de acesso ao Console Web do MinIO"
  value       = "http://${local.worker1_public_ip}:30901"
}

output "minio_api_url" {
  description = "Endpoint da API S3 do MinIO"
  value       = "http://${local.worker1_public_ip}:30900"
}

output "ansible_run_command" {
  description = "Comando para executar o provisionamento do cluster e servicos via Ansible"
  value       = "ansible-playbook -i ansible/inventory/hosts.magalu.yml ansible/site.yml"
}

output "ssh_master_command" {
  description = "Comando para conectar via SSH no nó Master"
  value       = "ssh -i ${var.ssh_private_key_path} ${var.ssh_user}@${local.master_public_ip}"
}
