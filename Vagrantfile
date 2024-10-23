# -*- mode: ruby -*-
# vi: set ft=ruby :
CUSTOMER = "TEST_CUSTOMER"
PROJECT  = "TEST_PROJECT"
HOSTNAME = "securitybits"
KEYBOARD = "se"
TIMEZONE = "Europe/Stockholm"

# kalilinux/rolling                    (virtualbox, 2024.2.0, (amd64))
# mayfly/windows10                     (virtualbox, 2024.01.06)

Vagrant.configure("2") do |config|

    ENV['VAGRANT_DEFAULT_PROVIDER'] = 'virtualbox'
    boxes = [
        { :name => "Kali",     :box => "kalilinux/rolling", :os => "linux", :box_version => "2024.2.0" },
        { :name => "Windows",  :box => "mayfly/windows10",  :os => "windows", :size => "80GB" }
    ]

    config.vm.provider "virtualbox" do |vb|
        vb.memory = 4000
        vb.cpus = 4
    end

    config.vm.network "forwarded_port", guest: 3389, host: 3389, id: 'rdp', auto_correct: true, disabled: true
    config.vm.network "forwarded_port", guest: 22, host: 2222, id: 'ssh', auto_correct: true, disabled: false

    config.vm.usable_port_range = 5000..5500

    # no autoupdate if vagrant-vbguest is installed
    if Vagrant.has_plugin?("vagrant-vbguest") then
        config.vbguest.auto_update = false
    end

    unless Vagrant.has_plugin?("vagrant-reload")
        puts 'Installing vagrant-reload Plugin...'
        system('vagrant plugin install vagrant-reload')
    end

    config.vm.boot_timeout = 600
    config.vm.graceful_halt_timeout = 600
    config.winrm.retry_limit = 30
    config.winrm.retry_delay = 10

    boxes.each do |box|
        config.vm.define box[:name] do |target|
            target.vm.provider "virtualbox" do |vb|
                vb.name = CUSTOMER + "_" + PROJECT + "_" + box[:name]
                vb.customize ["modifyvm", :id, "--groups", "/Pentest"]
            end
        

            target.vm.box_download_insecure = box[:box]
            target.vm.box = box[:box]
            if box.has_key?(:box_version)
                target.vm.box_version = box[:box_version]
            end

            # issues/49
            target.vm.synced_folder '.', '/Scripts', disabled: true
            target.vm.synced_folder 'Shared', '/Shared', disabled: false

            # IP
            if box.has_key?(:ip)
                target.vm.network :private_network, ip: box[:ip]
            end

            # OS specific
            if box[:os] == "windows"
                target.vm.guest = :windows
                target.vm.communicator = "winrm"

                target.vm.provision :shell, :path => "./Scripts/windows/Install-WMF3Hotfix.ps1", privileged: false
                target.vm.provision :shell, :path => "./Scripts/windows/ReArm.ps1", privileged: true
                target.vm.provision :shell, :path => "./Scripts/windows/Set-Locale.ps1", privileged: true
                target.vm.provision :shell, :path => "./Scripts/windows/Download_Commando.ps1", privileged: false

                target.vm.provision :file, :source => "./Scripts/windows/files/profile.xml", :destination => "c:\\tmp\\commando-vm-main\\Profiles\\Default.xml"
                target.vm.provision :file, :source => "./Scripts/windows/files/config.xml", :destination => "c:\\tmp\\commando-vm-main\\Profiles\\Configs\\win10config.xml"
                target.vm.provision :file, :source => "./Scripts/windows/files/background.png", :destination => "c:\\tmp\\commando-vm-main\\Images\\background.png"
                
            else
                target.vm.communicator = "ssh"
                target.vm.synced_folder '.', '/vagrant', disabled: false
                target.vm.provision "shell", path: "./Scripts/linux/provision/provision.sh", :args => "--keyboard=se"

                target.vm.provision "ansible_local" do |ansible|
                    ansible.install_mode = "pip"
                    ansible.pip_install_cmd = "sudo apt install python3-pip -y"
                    ansible.playbook = "./Scripts/linux/playbook.yml"
                    ansible.extra_vars = "./Scripts/linux/vars.yml"
                end
            end

            if box.has_key?(:size)
                target.vm.disk :disk, size: box[:size], primary: true
                if box[:os] == "windows"
                    target.vm.provision :shell, :path => "./Scripts/windows/Resize-Primary.ps1"
                end
            end

            if box.has_key?(:forwarded_port)
                # forwarded port explicit
                box[:forwarded_port] do |forwarded_port|
                    target.vm.network :forwarded_port, guest: forwarded_port[:guest], host: forwarded_port[:host], host_ip: "127.0.0.1", id: forwarded_port[:id]
                end
            end
        end
    end
end
