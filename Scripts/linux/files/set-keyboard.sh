#!/usr/bin/env bash
set -euo pipefail

layout="${1:?Usage: workbox-keyboard LAYOUT}"
if [[ ! "$layout" =~ ^[a-zA-Z0-9_]+[a-zA-Z0-9_-]*(,[a-zA-Z0-9_]+[a-zA-Z0-9_-]*)*$ ]]; then
    printf 'Invalid XKB layout: %s\n' "$layout" >&2
    exit 1
fi

# Pause Xfce overrides until layout and variant form a consistent pair.
xfconf-query --channel keyboard-layout --property /Default/XkbDisable --create --type bool --set true
xfconf-query --channel keyboard-layout --property /Default/XkbLayout --create --type string --set "$layout"
xfconf-query --channel keyboard-layout --property /Default/XkbVariant --create --type string --set ''
xfconf-query --channel keyboard-layout --property /Default/XkbDisable --create --type bool --set false
