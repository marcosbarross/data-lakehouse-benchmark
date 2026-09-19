resource "mgc_network_security_groups" "cluster_sg" {
  name        = "${var.cluster_prefix}-cluster-sg"
  description = "Grupo de seguranca para o cluster K3s Lakehouse"
}

# --- Regras Ingress de Administracao e Acesso Externo ---
resource "mgc_network_security_groups_rules" "allow_ssh" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir SSH"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_k3s_api" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir K3s API Server"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 6443
  port_range_max    = 6443
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_trino_ui" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir Trino Coordinator NodePort"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 30080
  port_range_max    = 30080
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_minio_api" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir MinIO API NodePort"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 30900
  port_range_max    = 30900
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_minio_console" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir MinIO Console NodePort"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 30901
  port_range_max    = 30901
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_postgres" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir Postgres NodePort"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 30432
  port_range_max    = 30432
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_grafana" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir Grafana NodePort"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 30300
  port_range_max    = 30300
  remote_ip_prefix  = var.allowed_admin_cidr
}

resource "mgc_network_security_groups_rules" "allow_prometheus" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir Prometheus NodePort"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 30090
  port_range_max    = 30090
  remote_ip_prefix  = var.allowed_admin_cidr
}

# --- Comunicacao Interna do Cluster K3s (Flannel, Kubelet, Pods) ---
resource "mgc_network_security_groups_rules" "allow_cluster_internal_tcp" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir trafego TCP interno do cluster"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 1
  port_range_max    = 65535
  remote_ip_prefix  = "10.0.0.0/8"
}

resource "mgc_network_security_groups_rules" "allow_cluster_internal_udp" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir trafego UDP interno (Flannel VXLAN)"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "udp"
  port_range_min    = 1
  port_range_max    = 65535
  remote_ip_prefix  = "10.0.0.0/8"
}

resource "mgc_network_security_groups_rules" "allow_cluster_internal_172_tcp" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir trafego TCP interno entre nós do cluster (faixa 172.16.0.0/12)"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 1
  port_range_max    = 65535
  remote_ip_prefix  = "172.16.0.0/12"
}

resource "mgc_network_security_groups_rules" "allow_cluster_internal_172_udp" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir trafego UDP interno entre nós do cluster (faixa 172.16.0.0/12)"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "udp"
  port_range_min    = 1
  port_range_max    = 65535
  remote_ip_prefix  = "172.16.0.0/12"
}

resource "mgc_network_security_groups_rules" "allow_cluster_internal_flannel_fallback" {
  security_group_id = mgc_network_security_groups.cluster_sg.id
  description       = "Permitir Flannel VXLAN porta 8472"
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "udp"
  port_range_min    = 8472
  port_range_max    = 8472
  remote_ip_prefix  = "0.0.0.0/0"
}
