# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-24.04"
  
  config.vm.box_check_update = false

  ansible_playbook = File.expand_path("ansible/site.yml", __dir__)
  ansible_inventory = File.expand_path("ansible/inventory/hosts.yml", __dir__)
  ansible_binary = File.expand_path("env/bin/ansible-playbook", __dir__)

  nodes = [
    { name: "k3s-master",  ip: "192.168.56.80", cpus: 2, mem: 2048 },
    { name: "k3s-worker1", ip: "192.168.56.81", cpus: 2, mem: 8192 },
    { name: "k3s-worker2", ip: "192.168.56.82", cpus: 2, mem: 4096 }
  ]

  nodes.each do |node|
    config.vm.define node[:name] do |subconfig|
      subconfig.vm.hostname = node[:name]
      
      subconfig.vm.network "private_network", ip: node[:ip]

      subconfig.vm.provider "virtualbox" do |vb|
        vb.name = "tcc-#{node[:name]}"
        vb.memory = node[:mem]
        vb.cpus = node[:cpus]
        
        vb.customize ["modifyvm", :id, "--ioapic", "on"]
        vb.customize ["modifyvm", :id, "--natdnshostresolver1", "on"]
      end

      subconfig.vm.provision "shell", inline: <<-SHELL
        apt-get update
        apt-get install -y python3 python3-pip avahi-daemon libnss-mdns
      SHELL
    end
  end

  config.trigger.after :provision do |trigger|
    trigger.info = "Executando Ansible para provisionar o Lakehouse..."
    trigger.run = {
      inline: "cd #{File.dirname(__FILE__)} && #{ansible_binary} -i #{ansible_inventory} #{ansible_playbook}"
    }
  end
end