#!/bin/sh
# ------------------------------------------------------------
# tools/net_config_common.sh
#
# NetworkManager 1.42 configuration for Raspberry-Pi cameras
# ------------------------------------------------------------
# • Use ONE wired profile (“Wired connection 1”)
#     – Primary: DHCP
#     – Fallback: IPv4 link-local (169.254/16) if no DHCP server
# • Delete the legacy eth0-ll profile so the interface can never
#   get “stuck” on link-local only.
# • Keep the link-local address out of routing and DNS tables.
# ------------------------------------------------------------
set -e        # Abort on any error

# ------------------------------------------------------------
# 1. Configure the main wired profile
#    - ipv4.method auto ........ normal DHCP
#    - ipv4.link-local enabled . also add 169.254/16 when DHCP absent
#    - ipv4.dhcp-timeout 15 .... wait 15 s before falling back
#    - ipv4.may-fail yes ....... treat missing DHCP as non-fatal
#    - connection.autoconnect-retries 0
#                               retry DHCP forever in background
# ------------------------------------------------------------
sudo nmcli connection modify "Wired connection 1" \
        ipv4.method auto \
        ipv4.link-local enabled \
        ipv4.dhcp-timeout 15 \
        ipv4.may-fail yes \
        connection.autoconnect-priority 0 \
        connection.autoconnect-retries 0

# ------------------------------------------------------------
# 4. Activate the updated profile immediately
# ------------------------------------------------------------
sudo nmcli connection up "Wired connection 1"
