#!/bin/sh
# Set up config files for NTP clients of breathecam_ntp.local

set -e # exit on first error

# avahi-daemon.default.conf is indeed the default file, which we
# install on the client machines in case it was overwritten with the
# .clock.conf version previously.

cd ~/breathecam/Code/pi_cam/config_files/
sudo cp -p avahi-daemon.default.conf /etc/avahi/avahi-daemon.conf 
sudo cp -p ntp.client.conf /etc/ntpsec/ntp.conf
