#!/bin/sh
# Set up config files for NTP clients of breathecam_ntp.local
set -e                                   # exit on first error

cd ~/breathecam/Code/pi_cam/config_files/

sudo cp -p avahi-daemon.default.conf /etc/avahi-daemon.conf
sudo cp -p ntp.client.conf /etc/ntpsec/ntp.conf

# 1) Restart the NTP daemon to load the new configuration
echo "Restarting ntpsec.service ..."
sudo systemctl restart ntpsec.service

# 2) Wait (up to 60 s) for the clock to synchronise
echo -n "Waiting for NTP sync"
for i in $(seq 1 30); do                 # 30 × 2 s = 60 s max
    if ntpstat >/dev/null 2>&1; then
        echo "  synchronised."
        break
    fi
    sleep 2
    echo -n "."
done

if ! ntpstat >/dev/null 2>&1; then
    echo "  timed out after 60 s; check ntpq -p."
    exit 1
fi

# 3) Commit the disciplined system time to the RTC
echo "Writing time to RTC ..."
sudo hwclock -w
echo "Done."
