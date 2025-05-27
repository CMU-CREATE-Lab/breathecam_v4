#!/bin/sh

# Network configuration needed on all hosts in quad pi to allow
# communication via link-local addresses when there is no DHCP server.
# This is to access the local DHCP server breathecam_ntp.local in the
# quad configuration.
set -e

# ----- 1) Tweak the existing DHCP profile --------------------
sudo nmcli connection modify "Wired connection 1"  \
        ipv4.method auto                          \
        ipv4.dhcp-timeout 15                      \
        ipv4.may-fail yes                         \
        connection.autoconnect-priority 0

# ----- 2) Ensure exactly ONE link-local fall-back profile ----
if nmcli --terse --fields NAME connection show | grep -q '^eth0-ll$'; then
    echo "Updating existing eth0-ll profile ..."
    sudo nmcli connection modify eth0-ll          \
            ipv4.method link-local                \
            ipv4.may-fail yes                     \
            connection.autoconnect-priority -20
else
    echo "Creating eth0-ll profile ..."
    sudo nmcli connection add type ethernet ifname eth0 con-name eth0-ll \
            ipv4.method link-local                \
            ipv4.may-fail yes                     \
            connection.autoconnect-priority -20
fi
