#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd -- "$repo_root"

missing=()
for tool in ruby yamllint shellcheck ansible-lint ansible-playbook python3 git; do
    command -v "$tool" >/dev/null 2>&1 || missing+=("$tool")
done
if ((${#missing[@]})); then
    printf 'Missing validation tools: %s\n' "${missing[*]}" >&2
    exit 1
fi

# Explicit inputs keep ignored credentials, client data, and Adaptix out of checks.
yaml_files=(
    .yamllint.yml .ansible-lint
    .github/workflows/validate.yml
    config/defaults.yml config/engagement.example.yml
    Scripts/linux/vars.yml
    Scripts/linux/requirements.yml Scripts/linux/playbook.yml
    tests/fixtures/vars.yml
)
for playbook in Scripts/linux/ansible/*.yml; do
    [[ "${playbook,,}" == *adaptix* ]] || yaml_files+=("$playbook")
done
shell_files=(
    Scripts/validate.sh Scripts/linux/provision/provision.sh
    Scripts/linux/files/set-wallpaper.sh Scripts/linux/files/set-keyboard.sh
)

printf 'Checking YAML formatting...\n'
yamllint -f parsable -c .yamllint.yml "${yaml_files[@]}"
printf 'Checking shell syntax and lint...\n'
for script in "${shell_files[@]}"; do
    bash -n "$script"
done
shellcheck "${shell_files[@]}"
printf 'Checking Ruby syntax without evaluating Vagrant configuration...\n'
ruby -c Vagrantfile
printf 'Checking provisioning contracts...\n'
python3 tests/test_provisioning.py
python3 tests/test_wallpaper.py
python3 tests/test_keyboard.py
python3 tests/test_tool_repositories.py
printf 'Checking Ansible syntax using dummy configuration...\n'
ansible-playbook -i localhost, -c local --syntax-check Scripts/linux/playbook.yml \
    --extra-vars "@$repo_root/tests/fixtures/vars.yml"
printf 'Checking Ansible lint without downloading dependencies...\n'
ansible-lint --offline -c .ansible-lint Scripts/linux/playbook.yml
printf 'All validation checks passed. No VM was provisioned.\n'
