# Work-Boxes

Vagrant-managed Kali and optional Windows workstations for separate pentest
engagements. VirtualBox runs the VMs, Ansible configures Kali inside the guest,
and PowerShell provisions the custom Commando VM box.

## Quick Start

You need Vagrant, VirtualBox, hardware virtualization, and internet access.
The Vagrantfile installs `vagrant-reload` if missing. Ansible and Docker are
installed inside Kali, not required on the host.

Run the PowerShell examples from the repository root.

### 1. Create Your Engagement File

```powershell
if (-not (Test-Path config/engagement.yml)) {
    Copy-Item config/engagement.example.yml config/engagement.yml
}
New-Item -ItemType Directory -Path Shared -Force | Out-Null
```

Edit `config/engagement.yml`:

| Setting | What to provide |
| --- | --- |
| `engagement.customer`, `engagement.project` | Client and project labels used in VM names. |
| `engagement.hostname` | Guest hostname. |
| `engagement.shared_folder` | An existing host directory for this engagement's data. |
| `linux.user.name` | Your Kali workstation account. |
| `linux.user.password_hash` | A password hash, not a plaintext password. |
| `machines.Kali.enabled`, `machines.Windows.enabled` | Unquoted YAML `true` or `false`. |

Relative shared-folder paths resolve from the repository root. Use an absolute
path to keep client data elsewhere, and create that directory before starting.

### 2. Set the Kali Password

Generate a SHA-512 hash interactively:

```powershell
wsl openssl passwd -6
```

On Linux, use `openssl passwd -6`. Put the result in
`linux.user.password_hash`, enclosed in single quotes, replacing the empty
placeholder. Keep the engagement file private; it is ignored by Git.

Passwords are only set when creating the account. Changing the hash does not
reset an existing password; use `passwd` inside Kali. Changing the username does
not rename or remove an existing account.

### 3. Start and Log In

```powershell
vagrant up Kali
```

The first start runs provisioning. Log into the VirtualBox desktop using
`linux.user.name` and the password used to generate the hash.

`vagrant ssh Kali` connects as the box's Vagrant account, not your workstation
account. Inside the guest, use `sudo -iu user`, replacing `user` with your name.

## Daily Use

| Action | Host command |
| --- | --- |
| Machine status | `vagrant status` |
| Start enabled machines | `vagrant up` |
| Apply provisioning changes | `vagrant provision Kali` |
| Reboot / apply VM settings | `vagrant reload Kali` |
| Open a guest terminal | `vagrant ssh Kali` |
| Shut down machines | `vagrant halt` |
| Show forwarded ports | `vagrant port Kali` |

Use a machine name to target Kali or Windows. Starting an existing machine does
not normally rerun provisioning.

## Configuration

| File | Purpose |
| --- | --- |
| `config/engagement.yml` (local, ignored) | Client details, VM overrides, and Kali account credentials. |
| [config/engagement.example.yml](config/engagement.example.yml) | Template for a new engagement. |
| [config/defaults.yml](config/defaults.yml) | Shared VM, box, resource, and regional defaults. |
| [Scripts/linux/vars.yml](Scripts/linux/vars.yml) | Shared shell/group settings, extra packages, and references to the engagement account. |
| [TODO.md](TODO.md) | Project backlog. |

**Engagement settings override defaults**, including machine enablement.
To disable Windows for an engagement, set `machines.Windows.enabled: false`
in `config/engagement.yml`; changing only the defaults will not override a local
`true`. At least one machine must be enabled.

Nested mappings merge; arrays and scalar values replace their defaults.
Currently, Kali is enabled and Windows disabled in both defaults and the example.

Common overrides in `config/engagement.yml`:

- `provider.memory` and `provider.cpus`: default to 4000 MB and 4 CPUs **per enabled VM**.
- `linux.locale.keyboard` and `linux.locale.timezone`: default to `se` and `Europe/Stockholm`.
- `windows.locale.language` and `windows.locale.timezone`: Windows regional settings.
- `machines.<name>.hostname`, `box`, `box_version`, `disk_size`, and `ip`: optional machine overrides.
- `machines.<name>.forwarded_ports`: entries with `guest`, `host`, `id`, and optional `host_ip`.

Additional port forwards default to host loopback (`127.0.0.1`). Forwarding a
port does not make a service bound only to guest localhost reachable.
Keep both Linux and Windows locale defaults present, even when one VM is disabled.

Add Kali packages to `workbox_extra_tools` in `Scripts/linux/vars.yml`, then
reprovision. Removing a package from the list does not uninstall it.
The old `Scripts/linux/vars.local.yml` is no longer loaded.

## Switching Engagements

**Do not reuse an existing VM for another client just by changing the YAML.**
The checkout's `.vagrant/` state, VM disks, and Docker volumes can retain data.

1. Back up the shared directory and any required guest-only files or Docker data.
2. With the old engagement configuration still active, run `vagrant destroy`.
3. Archive the old data and select a separate shared directory.
4. Update `config/engagement.yml`, create the new directory, and start the VMs.

`vagrant destroy` deletes VM disks, not the host shared directory.

Both enabled VMs share the engagement directory at `/Shared`. Kali also sees the
repository at `/vagrant`, including the ignored engagement file and password hash.
This separates work operationally; it is not a hardened boundary against a
compromised guest. Git ignores are neither encryption nor backups.

## What Gets Provisioned

Kali's bootstrap intentionally refreshes its archive keyring and APT index on
every provisioning run. It does not perform a full system upgrade.
Vagrant installs Ansible and the declared
[collection requirements](Scripts/linux/requirements.yml), then runs
[playbook.yml](Scripts/linux/playbook.yml) in this order:

| Playbook | Purpose |
| --- | --- |
| [locale.yml](Scripts/linux/ansible/locale.yml) | Timezone, system keyboard, console keymap cache, and Xfce keyboard setup. |
| [user.yml](Scripts/linux/ansible/user.yml) | Workstation account, home, SSH key, and additive group membership. |
| [tools.yml](Scripts/linux/ansible/tools.yml) | Base and extra Kali packages. |
| [dotfiles.yml](Scripts/linux/ansible/dotfiles.yml) | Alacritty, Neovim, fzf, ripgrep, tmux, and user-owned Git/Stow configuration. |
| [wallpaper.yml](Scripts/linux/ansible/wallpaper.yml) | Custom wallpaper at the workstation user's Xfce login. |
| [docker.yml](Scripts/linux/ansible/docker.yml) | Docker, Compose, service startup, and user group access. |
| [bloodhound.yml](Scripts/linux/ansible/bloodhound.yml) | Checksum-verified BloodHound CLI, without deploying CE containers. |
| [vscode.yml](Scripts/linux/ansible/vscode.yml) | Microsoft repository and VS Code. |

Dotfiles are cloned into `~/.dotfiles` from
[Securitybits-io/.dotfiles](https://github.com/Securitybits-io/.dotfiles).
Stow checks conflicts before linking; existing files and Git edits are not
forcibly overwritten. Reprovisioning can fetch updates from the configured branches.

### Keyboard and Wallpaper

The desktop hooks target **Xfce/X11**. Keyboard settings are applied at login;
a reboot activates the updated console keymap. For an existing machine:

```powershell
vagrant provision Kali
vagrant reload Kali
```

Check `setxkbmap -query` in an Xfce terminal for `layout: se`.
An SSH terminal uses the host's keyboard and is not a guest layout test.

Replace [config/files/kali-bg.png](config/files/kali-bg.png) and reprovision to
change the wallpaper. It is reapplied at each workstation-user login, using
zoom-to-fill across workspaces. It does not change the login-screen background.

To apply it immediately, or after adding a display, run this **inside that user's
Xfce terminal**, without sudo:

```bash
/usr/local/bin/workbox-wallpaper /usr/local/share/backgrounds/workbox/kali-bg.png
```

### BloodHound CE

The CLI is installed automatically; CE itself is not. Allocate at least 8192 MB
RAM to Kali before deploying CE, with additional resources for other tools.
See the [CE quickstart](https://bloodhound.specterops.io/get-started/quickstart/community-edition-quickstart)
for requirements and access details.

In a fresh login as the workstation user, without sudo:

```bash
docker info
docker compose version
bloodhound-cli install
```

Docker group membership takes effect at a new login and grants root-equivalent
access within the VM. Follow the CLI output for initial credentials and the
guest-local UI.

### Optional Windows VM

Register your custom box, then enable Windows in the engagement file:

```powershell
vagrant box add --name commando/default --provider virtualbox D:/Boxes/commando-default.box
vagrant up Windows
```

The box must already contain the Commando VM Default profile. The
[Windows scripts](Scripts/windows) retain rearm behavior, apply regional/Explorer
settings, and expand the primary partition when configured. User-specific settings
apply to the provisioning account; the Kali account settings do not create a
Windows user.

## Validation and Troubleshooting

From PowerShell, with the Linux tools available in WSL:

```powershell
wsl bash Scripts/validate.sh
```

On Linux, run `bash Scripts/validate.sh`. It requires Ruby, Python 3 with PyYAML,
yamllint, ShellCheck, ansible-core, ansible-lint, and the collection declared in
`Scripts/linux/requirements.yml`. Install that collection as the validation user
with `ansible-galaxy collection install -r Scripts/linux/requirements.yml`.

Validation checks YAML, shell/Ruby syntax, provisioning contracts, helper behavior,
and Ansible syntax/lint. It uses dummy credentials, does not install missing tools,
and does not start VMs. These checks do not prove that desktop login hooks work in
a live guest.

| Symptom | Check |
| --- | --- |
| Windows is unexpectedly enabled | Check the override in `config/engagement.yml`, not only the defaults. |
| Account task fails with hidden output | Check the username and nonempty password hash in the engagement file. |
| Stow or Git reports a conflict | Inspect and back up the specific conflicting files; provisioning does not force-reset them. |
| Wallpaper or keyboard is unchanged | Reprovision, then log out/in; reboot for console keyboard changes. |
| Docker permission denied | Use the workstation account and start a fresh login session. |
| BloodHound UI unavailable | Installing the CLI does not deploy CE; run `bloodhound-cli install`. |
| Ansible prints warnings | Read the message and final recap. Deprecation warnings are not failures; check `failed` and `unreachable`. |

Before using provisioning changes for client work, test a fresh disposable VM,
desktop login, keyboard/wallpaper, Docker access, and a second provisioning run.

## TODO

Keep agreed future work in [TODO.md](TODO.md), which currently has no active entries.
Adaptix remains under development and outside the normal provisioning and validation flow.
