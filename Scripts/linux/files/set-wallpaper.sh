#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

wallpaper="${1:?Usage: workbox-wallpaper IMAGE}"
if [[ ! -r "$wallpaper" ]]; then
    printf 'Wallpaper is not readable: %s\n' "$wallpaper" >&2
    exit 1
fi
command -v xfconf-query >/dev/null
if [[ "${XDG_SESSION_TYPE:-x11}" != x11 ]]; then
    printf 'This wallpaper helper requires an Xfce X11 session.\n' >&2
    exit 1
fi

# Xfce 4.20 keys backdrops by X11 screen and RandR connector, not monitor index.
outputs="$(xrandr --query)"
if [[ ! "$outputs" =~ ^Screen\ ([0-9]+): ]]; then
    printf 'Cannot determine the X11 screen from xrandr.\n' >&2
    exit 1
fi
screen="${BASH_REMATCH[1]}"

configured=false
while read -r connector status details; do
    [[ "$status" == connected && "$details" =~ [0-9]+x[0-9]+[+-][0-9]+[+-][0-9]+ ]] || continue
    backdrop="/backdrop/screen$screen/monitor$connector/workspace0"
    xfconf-query --channel xfce4-desktop --property "$backdrop/last-image" --create --type string --set "$wallpaper"
    xfconf-query --channel xfce4-desktop --property "$backdrop/image-style" --create --type int --set 5
    xfconf-query --channel xfce4-desktop --property "$backdrop/backdrop-cycle-enable" --create --type bool --set false
    configured=true
done <<< "$outputs"

if [[ "$configured" != true ]]; then
    printf 'No active X11 displays found; run this inside the Xfce desktop session.\n' >&2
    exit 1
fi

xfconf-query --channel xfce4-desktop --property /backdrop/single-workspace-number --create --type int --set 0
xfconf-query --channel xfce4-desktop --property /backdrop/single-workspace-mode --create --type bool --set true
