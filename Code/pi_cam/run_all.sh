#!/bin/sh
# You must run this as root for the watchdog reboot to work

cd /home/breathecam/breathecam/Code/pi_cam

# Don't do anything if run_inhibit exists
if [ -f config_files/run_inhibit ]; then
    echo "config_files/run_inhibit exists, not running anything"
    exit 0
fi

sudo su -c "mkdir -p logs" breathecam

# pingServer_launcher needs to run as root so that it can reboot

# pingServer_launcher needs to run as root so that it can reboot. setsid makes
# sure it is detached when we run this from the command line.
sudo setsid ./pingServer_launcher.sh > logs/pingServer.log 2>&1 &

sudo su -c "./imageService_launcher.sh 2>&1 >>logs/imageService.out &" breathecam

sudo su -c "./uploadToServer_launcher.sh 2>&1 >>logs/uploadToServer.out &" breathecam

echo "Compiling webConsole typescript"
sudo su -c "node_modules/.bin/tsc" breathecam

echo "Running webConsole"
sudo su -c "gunicorn -w 2 -b 0.0.0.0:8000 webConsole:app >> logs/webConsole.log 2>&1 &" breathecam
