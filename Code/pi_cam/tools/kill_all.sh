#!/bin/sh

cd /home/breathecam/breathecam/Code/pi_cam

# Kill launcher processes first to make sure they don't respawn the service
# after we kill it.
echo "Killing launchers:"
sudo pkill -f pingServer_launcher.sh
sudo pkill -f remoteDesktop_launcher.sh
sudo pkill -f imageService_launcher.sh
sudo pkill -f udpPinger_launcher.sh
sudo pkill -f uploadToServer_launcher.sh

sleep 1

echo "Killing services:"
sudo pkill -f pingServer.py
#pkill -f ??? remote desktop
sudo pkill -f imageService.py
sudo pkill -f udpPinger.py
sudo pkill -f uploadToServer.py
sudo pkill -f libcamera-still
sudo pkill -f webConsole
