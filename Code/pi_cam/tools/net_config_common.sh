#!/bin/sh
# Common network setup for all Pi boards (NM 1.42 style)
set -e

# 1) Make the main wired profile fall back to link local if DHCP is absent
sudo nmcli connection modify "Wired connection 1"          \
        ipv4.method auto                                   \
        ipv4.link-local enabled                            \
        ipv4.dhcp-timeout 15                               \
        ipv4.may-fail yes                                  \
        connection.autoconnect-priority 0                  \
        connection.autoconnect-retries 0                   \
        ipv4.never-default yes      # keep 169.254 route out of the way \
        ipv4.ignore-auto-dns yes    # and out of /etc/resolv.conf

# 2) Remove the old standalone link-local profile if it’s still around
if nmcli --terse --fields NAME connection show | grep -q '^eth0-ll$'; then
    echo "Deleting obsolete eth0-ll profile ..."
    sudo nmcli connection delete eth0-ll
fi

# 3) Activate the updated profile right away
sudo nmcli connection up "Wired connection 1"
