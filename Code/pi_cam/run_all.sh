#!/bin/sh
# You must run this as root for the watchdog reboot to work

# Define common paths
BASE_DIR=/home/breathecam/breathecam/Code/pi_cam
VENV_DIR=$BASE_DIR/.venv
LOG_DIR=$BASE_DIR/logs

# Change to the base directory
cd $BASE_DIR

# Don't do anything if run_inhibit exists
if [ -f config_files/run_inhibit ]; then
    echo "config_files/run_inhibit exists, not running anything"
    exit 0
fi

# Create logs directory as the breathecam user
sudo su -c "mkdir -p $LOG_DIR" breathecam

# pingServer_launcher needs to run as root so that it can reboot.
# setsid ensures it is detached when run from the command line.
sudo setsid bash -c "source $VENV_DIR/bin/activate && ./pingServer_launcher.sh > $LOG_DIR/pingServer.log 2>&1 &"

# imageService_launcher and uploadToServer_launcher should run as the breathecam user.
# Activate the virtual environment before running the scripts.
sudo su -c "source $VENV_DIR/bin/activate && ./imageService_launcher.sh >> $LOG_DIR/imageService.out 2>&1 &" breathecam
sudo su -c "source $VENV_DIR/bin/activate && ./uploadToServer_launcher.sh >> $LOG_DIR/uploadToServer.out 2>&1 &" breathecam

# Compile the TypeScript for the web console
echo "Compiling webConsole TypeScript"
sudo su -c "node_modules/.bin/tsc" breathecam

# Run the web console using Gunicorn.
# We need a long worker timeout because the worker loops during the entire image streaming.
# This is set to 15 minutes.
echo "Running webConsole"
sudo -u breathecam bash -c "cd $BASE_DIR && source $VENV_DIR/bin/activate && PYTHONPATH=$BASE_DIR gunicorn -w 2 -b 0.0.0.0:8000 webConsole:app --timeout 900 >> $LOG_DIR/webConsole.log 2>&1 &"
