#!/bin/bash

# Colors
RED="\033[01;31m"      # Errors
GREEN="\033[01;32m"    # Success
YELLOW="\033[01;33m"   # Warnings
BLUE="\033[01;34m"     # Information
BOLD="\033[01;01m"     # Highlight
NORMAL="\033[00m"      # Normal

# Check if run as root
if [ "$EUID" -ne 0 ]
    then echo -e "${RED}[!]${NORMAL} Please run as root"
    exit 1
fi
    echo -e " ${BLUE}[*]${RESET} ${BOLD}Starting Kali Linux setup script...${RESET}"
    sleep 2s

# Parameters default values
keyboard="se"

# Set parameters
while [ $# -gt 0 ]; do
    case "$1" in
        --keyboard=*)
            keyboard="${1#*=}"
            ;;
        *)
            echo -e "${RED}[!]${NORMAL} Invalid argument" 1>&2
            exit 1
    esac
    shift
done

# Check parameters
if [[ -n "${keyboard}" && -e /usr/share/X11/xkb/rules/xorg.lst ]]; then
    if ! $(grep -q " ${keyboard} " /usr/share/X11/xkb/rules/xorg.lst); then
        echo -e ' '${RED}'[!]'${NORMAL}" Keyboard layout '${keyboard}' is not supported" 1>&2
        exit 1
    fi
fi

# Update and upgrade packages
echo -e "\n\n ${GREEN}[+]${NORMAL} Packages ${GREEN}update${NORMAL}"
sudo apt-get update
# echo -e "\n\n ${GREEN}[+]${NORMAL} Packages ${GREEN}upgrade${NORMAL}"
# sudo apt-get upgrade -y

# Change keyboard layout
if [[ -n "${keyboard}" ]]; then
    echo -e "\n\n ${GREEN}[+]${NORMAL} Updating ${GREEN}location information${NORMAL} ~ keyboard layout (${BOLD}${keyboard}${NORMAL})"
    geoip_keyboard=$(curl -s http://ifconfig.io/country_code | tr '[:upper:]' '[:lower:]')
    [ "${geoip_keyboard}" != "${keyboard}" ] \
        && echo -e " ${YELLOW}[i]${NORMAL} Keyboard layout (${BOLD}${keyboard}${NORMAL}) doesn't match what's been detected via GeoIP (${BOLD}${geoip_keyboard}${NORMAL})"
    file=/etc/default/keyboard; #[ -e "${file}" ] && cp -n $file{,.bkup}
    sed -i 's/XKBLAYOUT=".*"/XKBLAYOUT="'${keyboard}'"/' "${file}"
else
    echo -e "\n\n ${YELLOW}[i]${NORMAL} ${YELLOW}Skipping keyboard layout${NORMAL} (missing: '$0 ${BOLD}--keyboard <value>${NORMAL}')..." 1>&2
fi