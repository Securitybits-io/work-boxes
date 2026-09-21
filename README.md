# Work-Boxes

Vagrant-managed Kali and Windows workstations for isolated pentest engagements.

## Configure an engagement

The committed `config/defaults.yml` contains reusable VM defaults. Client and
project-specific values belong in the ignored `config/engagement.yml` file.

Create a local engagement configuration from the example:

```powershell
Copy-Item config/engagement.example.yml config/engagement.yml
```

Set the customer, project, hostname, shared-data path, and enabled machines in
`config/engagement.yml`. Relative shared-folder paths are resolved from the
repository root; absolute paths can be used to keep client data elsewhere.
The selected shared folder must exist before Vagrant starts.

Linux regional defaults use `keyboard` and `timezone`. Windows uses the
`windows.language` and `windows.timezone` settings in `config/defaults.yml`.

## Daily workflow

Start every enabled machine:

```powershell
vagrant up
```

Start or provision one machine:

```powershell
vagrant up Kali
vagrant provision Kali
```

Before changing `config/engagement.yml` to another client or project, destroy
the current engagement VMs and archive or remove its shared-data directory:

```powershell
vagrant destroy
```

Vagrant keeps machine state under `.vagrant/`, so reusing existing machines
after changing engagement details would weaken the intended client separation.

## Configuration layout

- `config/defaults.yml`: committed provider, box, and regional defaults.
- `config/engagement.example.yml`: safe template for a new engagement.
- `config/engagement.yml`: ignored local client and project configuration.
- `Shared/`: ignored local data directory used by the default configuration.

Engagement values override matching defaults. Nested mappings are merged;
arrays and scalar values replace their defaults completely.
