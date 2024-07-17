# -*- mode: ruby -*-
# vi: set ft=ruby :
NAME = "CTF-Kali"
HOSTNAME = "securitybits"
KEYBOARD = "se"
TIMEZONE = "Europe/Stockholm"

Vagrant.configure("2") do |config|

    config.vm.box = "kalilinux/rolling"

    unless Vagrant.has_plugin?("vagrant-vmware-desktop")
        puts 'Installing vagrant-vmware-desktop Plugin...'
        system('vagrant plugin install vagrant-vmware-desktop')
    end

    unless Vagrant.has_plugin?("vagrant-reload")
        puts 'Installing vagrant-reload Plugin...'
        system('vagrant plugin install vagrant-reload')
    end

    config.vm.hostname = HOSTNAME

    config.vm.provider "vmware_desktop" do |v|
        v.gui = true
        v.vmx["memsize"] = "2048"
        v.vmx["numvcpus"] = "2"
        v.vmx["displayname"] = NAME
        v.vmx["ethernet0.pcislotnumber"] = "160"
    end

    config.vm.provision "shell", path: "provision/provision.sh", :args => "--keyboard=se"

#    config.vm.provision "file", source: "provision/openvas-update.sh", destination: "openvas-update.sh"

    config.vm.provision "ansible_local" do |ansible|
        ansible.playbook = "playbook.yml"
        ansible.extra_vars = "vars.yml"
    end
    
    config.vm.provision :reload

    $disable_vagrant = <<-SCRIPT
    usermod --expiredate 1 vagrant
    service sshd restart
    SCRIPT

    config.vm.provision "shell", inline: $disable_vagrant

end