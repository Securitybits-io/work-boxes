#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Provisioning must run as root." >&2
    exit 1
fi

echo "Refreshing the Kali archive keyring."
wget --quiet https://archive.kali.org/archive-keyring.gpg \
    --output-document /usr/share/keyrings/kali-archive-keyring.gpg

echo "Updating the package index."
apt-get update
