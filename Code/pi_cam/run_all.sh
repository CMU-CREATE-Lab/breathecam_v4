#!/bin/sh
# You must run this as root for the watchdog reboot to work

cd /home/breathecam/breathecam/Code/pi_cam

su -c "mkdir -p logs" breathecam

# pingServer_launcher needs to run as root so that it can reboot
# ./pingServer_launcher.sh &

#./remoteDesktop_launcher.sh &

#su -c "./imageService_launcher.sh 2>&1 >>logs/imageService.out" breathecam &

#./udpPinger_launcher.sh &

su -c "./uploadToServer_launcher.sh 2>&1 >>logs/uploadToServer.out" breathecam & 
