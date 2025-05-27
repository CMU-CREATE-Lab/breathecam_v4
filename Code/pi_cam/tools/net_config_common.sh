#!/bin/sh

# Network configuration needed on all hosts in quad pi to allow
# communication via link-local addresses when there is no DHCP server.
# This is to access the local DHCP server breathecam_ntp.local in the
# quad configuration.

# 1) normal wired profile (you already have this one)
sudo nmcli connection modify "Wired connection 1" \
        ipv4.method auto \
        ipv4.dhcp-timeout 15 \
        ipv4.may-fail yes \
        connection.autoconnect-priority 0

# 2) EXTRA link-local-only profile with lower priority
sudo nmcli connection add type ethernet ifname eth0 con-name eth0-ll \
        ipv4.method link-local \
        ipv4.may-fail yes \
        connection.autoconnect-priority -20
