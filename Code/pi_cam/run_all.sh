#!/bin/sh
# You must run this as root for the watchdog reboot to work

cd /home/breathecam/breathecam/Code/pi_cam

sudo su -c "/usr/local/bin/flask --app webConsole run --host=0.0.0.0 --port=8000" breathecam &

sudo su -c "mkdir -p logs" breathecam

# pingServer_launcher needs to run as root so that it can reboot
sudo ./pingServer_launcher.sh &

#./remoteDesktop_launcher.sh &

sudo su -c "./imageService_launcher.sh 2>&1 >>logs/imageService.out" breathecam &

#./udpPinger_launcher.sh &

sudo su -c "./uploadToServer_launcher.sh 2>&1 >>logs/uploadToServer.out" breathecam & 
