# Work-Boxes

A Vagrant workbench for keeping pentest workstations and engagement data separate
between clients. It provisions a Kali workstation and, optionally, a Windows
workstation based on a locally built Commando VM box.

The repository manages VM configuration and provisioning. Client identifiers,
local credentials, VM state, and engagement data stay outside tracked configuration.

## Contents

- [Technology and architecture](#technology-and-architecture)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Daily usage](#daily-usage)
- [Configuration reference](#configuration-reference)
- [Provisioning](#provisioning)
- [How-tos](#how-tos)
- [Validation](#validation)
- [Troubleshooting](#troubleshooting)
- [TODO and project status](#todo-and-project-status)
- [Repository layout](#repository-layout)

## Technology and architecture

| Component | Responsibility |
| --- | --- |
| Vagrant and Ruby | Read YAML settings, define machines, manage their lifecycle, and invoke provisioners. |
| VirtualBox | Run the VMs and provide shared folders and networking. The Vagrantfile selects this provider. |
| YAML | Separate reusable VM/Linux defaults from local engagement settings, including the Kali account. |
| Bash | Bootstrap Kali by refreshing its archive keyring and APT package index. |
| Ansible | Configure Kali through separate playbooks for locale, account, tools, dotfiles, Docker, BloodHound CLI, and VS Code. |
| PowerShell | Apply Windows regional settings, retained rearm behavior, and primary-partition expansion. |
| Git and GNU Stow | Clone the dotfiles and link configuration into the configured Kali user's home. |
| Docker and Compose | Provide the container runtime used by BloodHound CE and other local workloads. |

Vagrant runs Ansible **inside Kali**, using `ansible_local`. It installs Ansible
from the guest package manager when needed, then installs the declared collection
before invoking the main playbook. Normal VM provisioning does not require Ansible
or Docker on the Windows host. See the
[Ansible Local provisioner documentation](https://developer.hashicorp.com/vagrant/docs/provisioning/ansible_local).

### Engagement boundaries

- `config/engagement.yml` identifies the current client/project and selects its data folder.
- `.vagrant/` holds machine state for this checkout. Changing the engagement YAML does not create a separate state directory.
- The selected engagement directory is configured as a guest share at `/Shared` for each enabled VM.
- Kali explicitly mounts the repository at `/vagrant` for provisioning. This also exposes the ignored engagement file and its password hash.
- Both enabled VMs share the selected engagement folder. They are not isolated from each other's engagement data.

This is an organizational separation model, not a hardened isolation boundary
against a compromised guest. Ignoring files in Git is not encryption or backup.
Keep unrelated client data outside the checkout and the active shared directory.

## Requirements

### Host

- Vagrant and a compatible VirtualBox installation, with hardware virtualization enabled.
- Enough host memory and disk space for every enabled VM, the installed tools, and collected data.
- Internet access for required boxes, Kali packages, Ansible Galaxy, Git repositories, and release downloads.
- The `vagrant-reload` plugin. The Vagrantfile attempts to install it when missing; it can also be installed beforehand with `vagrant plugin install vagrant-reload`.
- A local `commando/default` VirtualBox box if Windows is enabled.

PowerShell examples below run on the host from the repository root. WSL is useful
for validation and generating password hashes, but is not required to run the VMs.
Equivalent Linux tooling can be used elsewhere.

### Box and resource defaults

| Setting | Committed default |
| --- | --- |
| Memory | 4000 MB per enabled VM |
| CPUs | 4 per enabled VM |
| Kali box | `kalilinux/rolling`, version `2026.2.0` |
| Windows box | `commando/default`, with the Commando VM Default profile already installed |
| Windows primary disk | `80GB` |
| Enabled machines | Both in defaults; the engagement example disables Windows |

The repository does not build or install the Commando VM base profile. Register
your existing local box before enabling Windows, replacing this example path:

```powershell
vagrant box add --name commando/default --provider virtualbox D:/Boxes/commando-default.box
vagrant box list
```

BloodHound CE needs more memory than the default Kali allocation. SpecterOps lists
at least 8 GB RAM, 4 CPU cores, and 10 GB disk space for CE itself. Allow additional
space for Kali and engagement data. See the
[official CE quickstart](https://bloodhound.specterops.io/get-started/quickstart/community-edition-quickstart).

## Quick start

### 1. Create local configuration

These commands preserve an existing engagement configuration:

```powershell
if (-not (Test-Path config/engagement.yml)) {
    Copy-Item config/engagement.example.yml config/engagement.yml
}
New-Item -ItemType Directory -Path Shared -Force | Out-Null
```

Edit `config/engagement.yml` to set the customer, project, hostname, enabled
machines, and shared folder. Relative paths resolve from the repository root.
Absolute host paths allow client data to live elsewhere. The folder must already
exist; the Vagrantfile does not create it.

### 2. Configure the Kali account

Set `linux.user.name` in `config/engagement.yml`. The engagement example uses
`user`. Set the password hash in the same file. Reusable shell and group defaults
remain in [Scripts/linux/vars.yml](Scripts/linux/vars.yml).

Generate a SHA-512 password hash interactively without putting the password in
command history:

```powershell
wsl openssl passwd -6
```

On Linux, the equivalent command is `openssl passwd -6`.
Set `linux.user.password_hash` in `config/engagement.yml` to the generated hash,
enclosed in single quotes. Replace the example's empty value before provisioning
Kali. The username, initial password hash, and client settings are all edited in
this one engagement file.

The engagement file is ignored by Git. Do not commit it or substitute a plaintext
password in the tracked defaults. `!` or `*` intentionally locks password login;
these are not usable passwords for a normal first-login setup.
Ignoring the engagement file does not remove credentials already present in Git history.

For older checkouts, move the previous `workbox_user_name` and the hash from
`Scripts/linux/vars.local.yml` into `linux.user.name` and `linux.user.password_hash`
in the engagement file. Verify the values before removing the old credential file.
Its Git ignore rule is retained defensively, but no playbook loads it anymore.

### 3. Start Kali

```powershell
vagrant up Kali
vagrant status
```

The initial start runs provisioning. The tools, configured account, dotfiles,
Docker, Compose, and BloodHound CLI are installed before provisioning completes.
BloodHound CE containers are not deployed at this stage.

### 4. Log in

Use the VirtualBox console for the desktop and log in with the account configured
in `linux.user.name` and the password used to generate the hash.

For a terminal:

```powershell
vagrant ssh Kali
```

This uses the box's Vagrant SSH account, not automatically the configured
workstation account. Inside Kali, switch to the latter; replace `user` if changed:

```bash
sudo -iu user
```

The workstation's generated SSH key is not automatically installed as an
authorized host-login key. Vagrant manages its own SSH connection.

## Daily usage

| Action | Host command |
| --- | --- |
| Show machine status | `vagrant status` |
| Start all enabled machines | `vagrant up` |
| Start one enabled machine | `vagrant up Kali` or `vagrant up Windows` |
| Apply provisioning changes | `vagrant provision Kali` |
| Reboot and apply VM settings | `vagrant reload Kali` |
| Reboot and run provisioning | `vagrant reload Kali --provision` |
| Shut down one machine | `vagrant halt Kali` |
| Shut down all machines | `vagrant halt` |
| Show assigned forwarded ports | `vagrant port Kali` |

Starting an existing machine does not normally rerun provisioning. Use
`vagrant provision` explicitly after editing playbooks or account/tool settings.
[Vagrant up documentation](https://developer.hashicorp.com/vagrant/docs/cli/up).

### Switching clients or projects

1. Finish the current engagement and back up required files, including data stored only on VM disks or in Docker volumes.
2. While the current engagement configuration is still active, destroy its VMs using the command below.
3. Archive the old shared directory and select a different directory for the next engagement.
4. Update `config/engagement.yml`, ensure the new data folder exists, then start the required machines.

**Destructive:** this removes the current VM disks. It does not erase the host
shared directory or replace the need for a backup.

```powershell
vagrant destroy
```

Do not reuse existing VM state for another client merely by changing the customer,
project, or shared-folder values. Local VM files and container volumes can retain
the previous client's data.

## Configuration reference

### Files and precedence

| File | Purpose | Tracked? |
| --- | --- | --- |
| [config/defaults.yml](config/defaults.yml) | Reusable provider, box, and regional defaults | Yes |
| [config/engagement.example.yml](config/engagement.example.yml) | Template for a new engagement | Yes |
| `config/engagement.yml` | Active client/project settings, VM overrides, and Kali account credentials | No |
| [Scripts/linux/vars.yml](Scripts/linux/vars.yml) | Reusable shell/group/tool settings and references to the engagement account | Yes |

Vagrant recursively merges engagement settings over VM defaults. Nested mappings
merge; arrays and scalar values replace their defaults. YAML aliases are disabled.
`Scripts/linux/vars.yml` is separate Ansible configuration, not part of that merge.
The account, Docker, dotfiles, and wallpaper playbooks each load the same engagement file;
their `workbox_user_name` and `workbox_user_password_hash` variables reference
`linux.user.name` and `linux.user.password_hash`. Those references do not store a
second username or hash. Standalone runs use the same source as full provisioning.
Vagrant passes only the Linux keyboard and timezone as extra variables; it does
not put the password hash into shell arguments.

### VM settings

| YAML key | Meaning |
| --- | --- |
| `engagement.customer`, `engagement.project` | Required labels; VirtualBox names become `<customer>_<project>_<machine>`. |
| `engagement.hostname` | Required default guest hostname; Vagrant manages it. |
| `engagement.shared_folder` | Existing host directory shared with the enabled VMs. |
| `engagement.vm_group` | VirtualBox group; defaults to `/Pentest`. |
| `provider.memory`, `provider.cpus` | Resource allocation for every enabled VM. Per-machine memory/CPU overrides are not currently implemented. |
| `linux.locale.keyboard`, `linux.locale.timezone` | Kali keyboard layout and timezone; defaults are `se` and `Europe/Stockholm`. |
| `linux.user.name`, `linux.user.password_hash` | Kali account identity and initial password hash, supplied in the ignored engagement file. |
| `windows.locale.language`, `windows.locale.timezone` | Windows language/culture and timezone; defaults are `en-SE` and `W. Europe Standard Time`. |
| `machines.<name>.enabled` | Whether Vagrant defines the machine. At least one must be enabled. |
| `machines.<name>.box`, `box_version`, `os` | Box name, optional version pin, and guest type (`linux` or `windows`). |
| `machines.<name>.hostname` | Optional override of the engagement hostname. |
| `machines.<name>.disk_size` | Optional primary-disk size; Windows also runs partition expansion. |
| `machines.<name>.ip` | Optional static private-network address. |
| `machines.<name>.forwarded_ports` | List of mappings with `guest`, `host`, `id`, and optional `host_ip`. |

Both Linux and Windows locale defaults must remain present even when only one
machine type is enabled. Use the engagement file for overrides, keeping client
identifiers out of committed defaults.

### Kali account settings

| Setting | Editable location | Meaning |
| --- | --- | --- |
| `linux.user.name` | `config/engagement.yml` | Workstation account used by user creation, dotfiles, and Docker. |
| `linux.user.password_hash` | `config/engagement.yml` | Initial password hash. |
| `workbox_user_primary_group` | `Scripts/linux/vars.yml` | Primary group, created if missing; defaults to `konsult`. |
| `workbox_user_shell` | `Scripts/linux/vars.yml` | Login shell; defaults to `/usr/bin/zsh`. |
| `workbox_user_groups` | `Scripts/linux/vars.yml` | Supplementary groups to add without removing existing memberships. These groups must exist in the guest. |
| `workbox_extra_tools` | `Scripts/linux/vars.yml` | Additional Kali APT package names. |

The account playbook creates the home directory and generates a 2048-bit RSA SSH
key at `.ssh/id_rsa` if one is not already present. Passwords are set only when
creating the account. Editing the hash and reprovisioning does not reset an
existing password; use `passwd` inside the guest for that.

Changing the configured username does not migrate or remove an old account.
Choose the account before creating an engagement VM.

## Provisioning

### Kali

[Scripts/linux/provision/provision.sh](Scripts/linux/provision/provision.sh)
runs first as root. It downloads Kali's archive keyring on every provisioning run
and then runs `apt-get update`. **This unconditional download is intentional and
is being retained.** No full system upgrade is performed by this script.

Vagrant then installs Ansible if needed and uses its Galaxy hook to install
`community.general` from [requirements.yml](Scripts/linux/requirements.yml),
currently pinned to `6.5.0`. The main
[playbook](Scripts/linux/playbook.yml) runs these components in order:

| Order | Playbook | Work performed |
| --- | --- | --- |
| 1 | [locale.yml](Scripts/linux/ansible/locale.yml) | Set timezone, system keyboard defaults, console keymap cache, and Xfce keyboard login configuration. |
| 2 | [user.yml](Scripts/linux/ansible/user.yml) | Validate settings and configure the workstation account. |
| 3 | [tools.yml](Scripts/linux/ansible/tools.yml) | Install the deduplicated base and extra package lists in one APT transaction. |
| 4 | [dotfiles.yml](Scripts/linux/ansible/dotfiles.yml) | Install workstation applications, clone configuration and TPM, and link Stow packages as the workstation user. |
| 5 | [wallpaper.yml](Scripts/linux/ansible/wallpaper.yml) | Install the custom background and configure an Xfce login hook for the workstation user. |
| 6 | [docker.yml](Scripts/linux/ansible/docker.yml) | Install Docker and Compose, enable/start Docker, and add the workstation user to its group. |
| 7 | [bloodhound.yml](Scripts/linux/ansible/bloodhound.yml) | Download, verify, and install BloodHound CLI. |
| 8 | [vscode.yml](Scripts/linux/ansible/vscode.yml) | Configure Microsoft's APT repository and install VS Code. |

### Dotfiles

The playbook installs Alacritty, Neovim, fzf, ripgrep, Git, Stow, tmux, fontconfig,
and ACL support for Ansible's user switching. It clones
[Securitybits-io/.dotfiles](https://github.com/Securitybits-io/.dotfiles) into
`~/.dotfiles` and tmux's plugin manager into `~/.tmux/plugins/tpm`.

Every non-hidden top-level directory in the dotfiles checkout is treated as a
Stow package. A simulation checks for conflicts before links are applied to the
user's home. The user's font cache is refreshed when notified. The dotfiles
repository's installer is not executed.

System packages are installed with elevated privileges; clones, symlinks, and
font-cache operations run as the configured workstation user. Existing files are
not automatically adopted or overwritten. Git local edits are not forcibly
discarded, so an incompatible update can stop provisioning.

The dotfiles and TPM default to the moving `main` and `master` branches.
Reprovisioning can therefore fetch configuration updates. Use specific revisions
in the playbook when a fixed configuration is required.

### Keyboard layout

`linux.locale.keyboard` defaults to `se` (standard Swedish). An engagement can
override it; Vagrant passes the merged setting to the locale playbook. The playbook
sets `XKBLAYOUT` and clears `XKBVARIANT` in `/etc/default/keyboard`, preserving
the keyboard model and special-key options. It does not change the UI language.

When keyboard settings change, handlers regenerate the saved console keymap and
refresh X11 input-device defaults. The console cache is generated with
`setupcon --keyboard-only --save-only`, avoiding a forced console change while X
may be active. A reboot activates the updated console map. See Debian's
[keyboard configuration](https://manpages.debian.org/trixie/keyboard-configuration/keyboard.5.en.html)
and [setupcon documentation](https://manpages.debian.org/trixie/console-setup/setupcon.1.en.html).

A system-wide Xfce autostart entry also applies that layout and clears a stale
per-user variant at each login, including for the engagement account. This prevents
an old Xfce user setting from retaining the US layout. Model, compose-key settings,
and shortcuts are left alone. The desktop hook targets Kali's Xfce/X11 session.

For an existing VM, provision and then reboot:

```powershell
vagrant provision Kali
vagrant reload Kali
```

Inside the configured user's Xfce terminal, these should report the configured
layout (`se` by default):

```bash
xfconf-query --channel keyboard-layout --property /Default/XkbLayout
setxkbmap -query
```

An SSH terminal uses the host's keyboard input; it is not a test of the guest's
graphical keyboard layout. For a standalone locale playbook run, pass
`workbox_keyboard` and `workbox_timezone` explicitly, as Vagrant normally does.

### Desktop wallpaper

[config/files/kali-bg.png](config/files/kali-bg.png) is copied to
`/usr/local/share/backgrounds/workbox/kali-bg.png`. The wallpaper playbook creates
an Xfce-only autostart entry for the account selected by `linux.user.name`.
At each Xfce/X11 login, the helper gets active display connectors from `xrandr`
and creates their wallpaper settings directly with
[xfconf-query](https://docs.xfce.org/xfce/xfconf/xfconf-query).
It enables [Apply to all workspaces](https://docs.xfce.org/xfce/xfdesktop/preferences#background),
uses zoom-to-fill, and disables wallpaper cycling. Other desktop settings remain
unchanged. The display-key format follows
[Xfce 4.20's backdrop implementation](https://github.com/xfce-mirror/xfdesktop/blob/xfce-4.20/src/xfdesktop-backdrop-manager.c).

There is no polling or dependency on an existing `last-image` property. This fixes
the fresh-profile case where the previous helper could wait for 30 seconds and
exit without configuring a wallpaper. Configuration is applied through the user's
session, not by overwriting XML files while Xfconf may be running.

This is configured during normal provisioning and takes effect on first login.
For an existing VM, run `vagrant provision Kali`, then log out of Xfce and back in.
To apply it immediately in the configured user's graphical terminal, run:

```bash
/usr/local/bin/workbox-wallpaper /usr/local/share/backgrounds/workbox/kali-bg.png
```

Run that command again after adding a display during a session. It needs the
graphical session's display and D-Bus environment; do not run it with `sudo` or
from a plain SSH session. This implementation targets Xfce/X11, not Wayland.

Replace the source PNG and reprovision to update it. The managed wallpaper is
reapplied at every Xfce login; this does not change the login-screen background
or configure other desktop environments.

### Docker and BloodHound

Kali packages `docker.io` and `docker-compose` provide Docker and the Compose
commands `docker compose` and `docker-compose`. Docker is started and enabled.
The configured user's Docker group membership takes effect in a new login session
and grants root-equivalent access inside the VM.

BloodHound CLI is installed at `/usr/local/bin/bloodhound-cli`, pointing into a
versioned directory below `/opt/bloodhound-cli`. The current pin is `v0.2.1`, with
SHA-256 checksums for AMD64 and ARM64 archives. This does not imply full ARM
support for the workbench: the VS Code repository is currently restricted to AMD64.

Provisioning does not fetch BloodHound container images, create a CE instance,
or start its containers. See [Start BloodHound CE](#start-bloodhound-ce).

### Windows

The Windows path connects over WinRM and assumes the custom `commando/default`
box already contains the Commando VM Default profile and the required base
accounts. Linux account variables do not create or modify a Windows account.

| Script | Work performed |
| --- | --- |
| [ReArm.ps1](Scripts/windows/ReArm.ps1) | Invoke the existing Windows rearm flow. Retained as-is and rerun during Windows provisioning. |
| [Set-Locale.ps1](Scripts/windows/Set-Locale.ps1) | Apply the configured timezone, language list, and culture; enable dragging window contents and show hidden files, protected files, and file extensions. |
| [Resize-Primary.ps1](Scripts/windows/Resize-Primary.ps1) | When `disk_size` is configured, expand the `C:` partition to its supported maximum if necessary. |

Language, culture, and `HKCU` Explorer settings apply to the provisioning account,
not automatically to every Windows user. The rearm and regional changes may need
a reboot or a fresh login before their effects are visible.

## How-tos

### Use a dedicated client directory and more RAM

Create the data directory on the host:

```powershell
New-Item -ItemType Directory -Path D:/Engagements/example-client/external-web -Force
```

An example `config/engagement.yml`:

```yaml
---
engagement:
  customer: example-client
  project: external-web
  hostname: workbox
  shared_folder: D:/Engagements/example-client/external-web

provider:
  memory: 8192
  cpus: 4

linux:
  user:
    name: user
    password_hash: ""  # Set the generated hash before provisioning Kali.

machines:
  Kali:
    enabled: true
  Windows:
    enabled: false
```

Memory and CPU overrides apply to all enabled VMs. Enable Windows only after
registering the local box and allowing for its additional host resource usage.
Follow the client-switch procedure before applying this to an existing engagement.

### Add or change tools

Add Kali package names to `workbox_extra_tools` in `Scripts/linux/vars.yml`, then:

```powershell
vagrant provision Kali
```

Keep general base packages in `ansible/tools.yml` and dotfiles application
dependencies in `ansible/dotfiles.yml`. Do not duplicate packages between them.
Removing a name from a list does not uninstall an already installed package.

For a new provisioning component, create a separate playbook in
`Scripts/linux/ansible/`, import it once in `Scripts/linux/playbook.yml` after
its prerequisites, and extend the validation checks as needed.

### Rerun one component

Inside an already provisioned Kali VM, these playbooks can be rerun separately:

```bash
sudo ansible-playbook -i localhost, -c local /vagrant/Scripts/linux/ansible/dotfiles.yml
sudo ansible-playbook -i localhost, -c local /vagrant/Scripts/linux/ansible/docker.yml
sudo ansible-playbook -i localhost, -c local /vagrant/Scripts/linux/ansible/bloodhound.yml
```

Each line runs one component and reads `/vagrant/config/engagement.yml` for the
account settings when needed. Dotfiles and Docker require the configured account
to exist. These standalone commands do not run Vagrant's bootstrap or Galaxy hook.
For the complete configuration, prefer `vagrant provision Kali` from the host.

### Start BloodHound CE

Allocate at least 8192 MB RAM before starting CE. In a fresh login session as the
configured workstation user inside Kali, check Docker and install CE:

```bash
docker info
docker compose version
bloodhound-cli install
```

Run the CLI without `sudo`, so its configuration belongs to your user. The install
command downloads the container images and deploys CE. Follow its output for the
initial credentials and open `http://localhost:8080/ui/login` in the Kali browser.
The standard CE configuration binds to guest localhost. See
[SpecterOps' installation instructions](https://bloodhound.specterops.io/get-started/quickstart/community-edition-quickstart).

To manage an existing instance, consult `bloodhound-cli --help`. To change the CLI
version installed by provisioning, update `bloodhound_cli_version` and both
matching archive checksums together in `ansible/bloodhound.yml`. Updating the
management CLI and updating the running CE containers are separate operations.

### Configure networking

SSH forwarding is enabled with host port 2222 and automatic conflict correction;
inspect the actual assignment with `vagrant port Kali`. The configured automatic
port range is 5000-5500. The default RDP forwarding rule is disabled.
The built-in SSH rule does not explicitly set `host_ip`; the loopback default
described below applies to additional forwards defined in engagement YAML.

Private networking and additional forwards are optional machine settings. Merge
this fragment into the existing `machines.Kali` entry, adjusting the address and
ports to your environment:

```yaml
machines:
  Kali:
    ip: 192.168.56.20
    forwarded_ports:
      - guest: 8443
        host: 8443
        host_ip: 127.0.0.1
        id: engagement-web
```

Apply network changes with `vagrant reload Kali`. A forward does not install a
service, open a guest firewall, or make a loopback-only guest service reachable.
`host_ip` defaults to `127.0.0.1` for these additional forwards. In particular,
forwarding a port alone is not sufficient to expose BloodHound's default
guest-localhost listener.

## Validation

From the repository root on Linux:

```bash
bash Scripts/validate.sh
```

From PowerShell, using the default WSL distribution:

```powershell
wsl bash Scripts/validate.sh
```

Required tools are Bash, Ruby, Python 3 with PyYAML, yamllint, ShellCheck,
ansible-core, ansible-lint, and the declared Ansible collection. Install that
collection as the same user who will run validation:

```bash
ansible-galaxy collection install -r Scripts/linux/requirements.yml
```

The collection pin matches the Ansible 2.14 validation baseline. The guest's
Ansible version comes from its package manager and is not pinned by this
repository; validate compatibility when changing either dependency.

The script does not install missing tools and fails if a prerequisite is absent.
It performs:

1. YAML formatting checks on the selected public configuration and playbooks.
2. Bash syntax checks and ShellCheck.
3. Ruby syntax checking without evaluating the Vagrantfile.
4. Ten static regression tests covering account loading, account handling, keyboard/wallpaper wiring, package ownership, dependencies, fixtures, and provisioning order.
5. Wallpaper-helper and keyboard-helper tests using fake display/settings commands, with no desktop changes.
6. Ansible syntax checking and offline linting.

`tests/fixtures/vars.yml` supplies dummy engagement account values and a locked-account placeholder.
Validation overrides `workbox_engagement_vars_file` to load that fixture instead
of the private engagement file.
The checks do not require local credentials or an engagement file. Shared data
and Adaptix are excluded. They do not start VMs, install Vagrant plugins, deploy
containers, or test connectivity to package repositories.

These checks are not proof of successful provisioning or full idempotence. Stow
linking and BloodHound archive extraction are skipped in Ansible check mode when
they cannot operate on files that would only be downloaded during a real run.

### Manual acceptance checklist

Use a disposable test engagement before relying on provisioning changes:

- [ ] Create a fresh Kali VM and complete provisioning.
- [ ] Log in as the configured user and check the application configuration and file ownership.
- [ ] Verify the custom wallpaper on first Xfce login and after logging out and back in.
- [ ] Check the Swedish keyboard in Xfce and at the VM console after reboot, not through an SSH terminal.
- [ ] Confirm Docker works without sudo after a new login.
- [ ] Reprovision and verify existing passwords, supplementary groups, and local configuration are preserved.
- [ ] If using Windows, verify the custom box, regional settings, rearm/reboot behavior, and partition size.
- [ ] If using BloodHound CE, deploy it with sufficient resources and verify the local UI.

These are test steps, not claims that live VM validation has already been completed.

## Troubleshooting

| Symptom | Check or action |
| --- | --- |
| Missing engagement configuration or shared folder | Create the local YAML from its example and ensure the configured host directory exists. |
| No machine is enabled | Set `machines.Kali.enabled` or `machines.Windows.enabled` to `true`. |
| `commando/default` cannot be found | Register the local VirtualBox box under that name, or disable Windows for this engagement. |
| Kali account task fails with hidden output | Check `linux.user.name` and the nonempty `linux.user.password_hash` in `config/engagement.yml`. Credential-task output is deliberately suppressed. |
| Changed hash does not change an existing password | This is intentional: passwords are set on account creation only. Change the password inside the VM. |
| Stow reports a conflict | Back up and move aside the specific conflicting file, then rerun dotfiles provisioning. Do not delete the whole configuration directory. |
| Git refuses a dotfiles update | Inspect local changes in `~/.dotfiles` or the TPM checkout. Provisioning does not force-reset them. |
| Docker reports permission denied | Use the configured workstation account and start a new login session. Check `id` and `systemctl status docker` inside Kali. |
| BloodHound CLI exists but the UI is unavailable | The CLI installation alone does not deploy CE. Run `bloodhound-cli install`, inspect its output, and confirm adequate VM memory. |
| BloodHound is reachable only inside Kali | Its default listener is guest-localhost. Use the guest browser or deliberately configure access according to SpecterOps' documentation. |
| Kali keyring download or APT update fails | Check guest network access, DNS, system time, and the reported repository error. The keyring refresh remains part of normal bootstrap. |
| Ansible cannot find `community.general.timezone` | Check Galaxy installation and install the requirements as the user running Ansible; another account's collection directory may not be visible. |
| Validation reports a missing tool | Install that tool in the Linux/WSL environment running the validator. Nothing is installed automatically. |

## TODO and project status

[TODO.md](TODO.md) is the source of truth for the active backlog. It currently
has no active entries. Add agreed future work there rather than maintaining a
second unchecked feature list in this README.

Implemented work:

- [x] YAML-driven Vagrant defaults and per-engagement overrides.
- [x] Vagrant-managed hostnames and grouped regional settings.
- [x] Namespaced Kali account references with username and password hash consolidated in the ignored engagement file.
- [x] Additive account groups and preservation of existing passwords.
- [x] Batched package installation with separated dotfiles dependencies.
- [x] User-owned dotfiles provisioning in the normal first-boot flow.
- [x] Custom Kali wallpaper applied in the configured user's Xfce session.
- [x] Docker, Compose, and checksum-verified BloodHound CLI provisioning.
- [x] Declared Ansible collection installation and static validation checks.

Retained decisions:

- Keep the unconditional Kali archive-keyring download in the bootstrap script.
- Use the single custom `commando/default` Windows box with its Default profile already installed.
- Keep the existing Windows rearm script.
- Leave Adaptix outside active provisioning and validation while it is under development.
- Install BloodHound CLI automatically, but deploy CE containers explicitly as the workstation user.

## Repository layout

```text
Vagrantfile                    VM definitions, YAML merging, provisioner wiring
config/
  defaults.yml                 Reusable VM defaults
  engagement.example.yml       Public engagement template
  engagement.yml               Local engagement and Kali credentials (ignored)
  files/kali-bg.png             Custom Kali desktop wallpaper
Scripts/
  linux/
    playbook.yml               Ordered Kali provisioning entrypoint
    vars.yml                   Shared defaults and engagement account references
    requirements.yml           Ansible collection requirements
    provision/provision.sh     Kali keyring and APT bootstrap
    files/set-wallpaper.sh     Xfce wallpaper login helper
    files/set-keyboard.sh      Xfce keyboard layout login helper
    ansible/                   Separate provisioning playbooks
  windows/                     Rearm, locale, and disk-expansion scripts
  validate.sh                  Static validation entrypoint
tests/
  fixtures/vars.yml            Dummy validation values
  test_provisioning.py         Provisioning regression checks
  test_wallpaper.py            Isolated wallpaper-helper tests
  test_keyboard.py             Isolated keyboard-helper tests
Shared/                        Default engagement data directory (ignored)
.vagrant/                      Vagrant state (ignored)
.gitattributes                 LF rules for shell and YAML files
.yamllint.yml                  YAML lint configuration
.ansible-lint                  Ansible lint settings and dummy-variable override
TODO.md                        Active backlog
```
