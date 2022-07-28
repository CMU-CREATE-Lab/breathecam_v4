# Installing on breathecam

### As user "breathecam":

    sudo apt update
    sudo apt install libfmt-dev libboost-program-options-dev libcamera-dev libjpeg62-turbo-dev libexif-dev
    cd ~
    git clone --recursive https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
    cd breathecam/Code/pi_cam_grab
    make

* Be sure you're using a recent version of libcamera or you might see errors like error: ‘SENSOR_TEMPERATURE’ is not a member of ‘libcamera::controls’.  Rerun apt update and apt install lines from above.


### Add to /var/spool/cron/crontabs:

    @reboot /home/breathecam/breathecam/Code/pi_cam/run_all.sh
