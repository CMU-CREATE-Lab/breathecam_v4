#!/bin/bash
put_quad cryo1 config_files/breathecam.ini breathecam/Code/pi_cam/config_files/breathecam.ini
run_quad cryo1 "cd breathecam/Code/pi_cam;tools/kill_all.sh;./run_all.sh"
put_quad cryo2 config_files/breathecam.ini breathecam/Code/pi_cam/config_files/breathecam.ini
run_quad cryo2 "cd breathecam/Code/pi_cam;tools/kill_all.sh;./run_all.sh"
