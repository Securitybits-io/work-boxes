# -*- mode: ruby -*-
# vi: set ft=ruby :

require "yaml"

def load_yaml(path)
  raise "Missing configuration file: #{path}" unless File.file?(path)

  data = YAML.safe_load(
    File.read(path, encoding: "UTF-8"),
    permitted_classes: [],
    aliases: false
  )

  raise "Expected a YAML mapping in #{path}" unless data.is_a?(Hash)

  data
rescue Psych::SyntaxError => e
  raise "Invalid YAML in #{path}: #{e.message}"
end

def deep_merge(defaults, overrides)
  defaults.merge(overrides) do |_key, default_value, override_value|
    if default_value.is_a?(Hash) && override_value.is_a?(Hash)
      deep_merge(default_value, override_value)
    else
      override_value
    end
  end
end

def required_string(settings, *path)
  value = settings.dig(*path)
  setting_name = path.join(".")

  raise "#{setting_name} is required" unless value.is_a?(String) && !value.strip.empty?

  value.strip
end

defaults_path = File.join(__dir__, "config", "defaults.yml")
engagement_path = File.join(__dir__, "config", "engagement.yml")
settings = deep_merge(load_yaml(defaults_path), load_yaml(engagement_path))

customer = required_string(settings, "engagement", "customer")
project = required_string(settings, "engagement", "project")
hostname = required_string(settings, "engagement", "hostname")
shared_folder_setting = required_string(settings, "engagement", "shared_folder")
vm_group = required_string(settings, "engagement", "vm_group")
keyboard = required_string(settings, "keyboard")
timezone = required_string(settings, "timezone")
windows_timezone = required_string(settings, "windows", "timezone")
windows_language = required_string(settings, "windows", "language")

hostname_pattern = /\A[a-zA-Z0-9][a-zA-Z0-9.-]*\z/
timezone_pattern = /\A[a-zA-Z0-9_+-]+(?:\/[a-zA-Z0-9_+-]+)*\z/
raise "engagement.hostname contains unsupported characters" unless hostname.match?(hostname_pattern)
raise "timezone contains unsupported characters" unless timezone.match?(timezone_pattern)

shared_folder = File.expand_path(shared_folder_setting, __dir__)
raise "Shared folder does not exist: #{shared_folder}" unless File.directory?(shared_folder)

provider = settings.fetch("provider")
machines = settings.fetch("machines")
raise "machines must be a YAML mapping" unless machines.is_a?(Hash)

enabled_machines = machines.select { |_name, machine| machine.fetch("enabled", false) }
raise "At least one machine must be enabled" if enabled_machines.empty?

ENV["VAGRANT_DEFAULT_PROVIDER"] = "virtualbox"

Vagrant.configure("2") do |config|
  config.vm.provider "virtualbox" do |vb|
    vb.memory = provider.fetch("memory")
    vb.cpus = provider.fetch("cpus")
  end

  config.vm.network "forwarded_port", guest: 3389, host: 3389, id: "rdp", auto_correct: true, disabled: true
  config.vm.network "forwarded_port", guest: 22, host: 2222, id: "ssh", auto_correct: true, disabled: false

  config.vm.usable_port_range = 5000..5500

  # No autoupdate if vagrant-vbguest is installed.
  config.vbguest.auto_update = false if Vagrant.has_plugin?("vagrant-vbguest")

  unless Vagrant.has_plugin?("vagrant-reload")
    puts "Installing vagrant-reload plugin..."
    system("vagrant plugin install vagrant-reload")
  end

  config.vm.boot_timeout = 600
  config.vm.graceful_halt_timeout = 600
  config.winrm.retry_limit = 30
  config.winrm.retry_delay = 10

  enabled_machines.each do |name, machine|
    config.vm.define name do |target|
      target.vm.provider "virtualbox" do |vb|
        vb.name = "#{customer}_#{project}_#{name}"
        vb.customize ["modifyvm", :id, "--groups", vm_group]
      end

      target.vm.box = machine.fetch("box")
      target.vm.box_version = machine["box_version"] if machine.key?("box_version")
      target.vm.box_download_insecure = machine.fetch("box_download_insecure", false)
      target.vm.hostname = machine.fetch("hostname", hostname)

      # The repository is not exposed through the generic /Scripts mount.
      target.vm.synced_folder ".", "/Scripts", disabled: true
      target.vm.synced_folder shared_folder, "/Shared", disabled: false

      target.vm.network :private_network, ip: machine["ip"] if machine.key?("ip")

      if machine.fetch("os") == "windows"
        target.vm.guest = :windows
        target.vm.communicator = "winrm"

        target.vm.provision :shell, path: "./Scripts/windows/ReArm.ps1", privileged: true
        target.vm.provision :shell,
                            path: "./Scripts/windows/Set-Locale.ps1",
                            args: ["-TimeZoneId", windows_timezone, "-LanguageTag", windows_language],
                            privileged: true
      else
        target.vm.communicator = "ssh"
        target.vm.synced_folder ".", "/vagrant", disabled: false
        target.vm.provision "shell", path: "./Scripts/linux/provision/provision.sh", args: "--keyboard=#{keyboard}"

        target.vm.provision "ansible_local" do |ansible|
          ansible.install_mode = "default"
          ansible.playbook = "./Scripts/linux/playbook.yml"
          ansible.extra_vars = "./Scripts/linux/vars.yml"
          ansible.raw_arguments = ["--extra-vars='hostname=#{hostname} timezone=#{timezone}'"]
        end
      end

      if machine.key?("disk_size")
        target.vm.disk :disk, size: machine.fetch("disk_size"), primary: true
        if machine.fetch("os") == "windows"
          target.vm.provision :shell, path: "./Scripts/windows/Resize-Primary.ps1"
        end
      end

      machine.fetch("forwarded_ports", []).each do |forwarded_port|
        target.vm.network :forwarded_port,
                          guest: forwarded_port.fetch("guest"),
                          host: forwarded_port.fetch("host"),
                          host_ip: forwarded_port.fetch("host_ip", "127.0.0.1"),
                          id: forwarded_port.fetch("id")
      end
    end
  end
end
