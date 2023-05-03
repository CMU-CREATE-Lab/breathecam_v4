# RPI SETUP

### Create raspbian image with Raspberry Pi Imager
- Select 32-bit raspbian
- Click on Advanced options and fill in
    - Set hostname from camera name: [cameraname][elementname]
      e.g. piquad3b where piquad3 is cameraname, and b is the
      elementname (a being “primary”).
        Current camera names for ecam: [http://ecam.cmucreatelab.org/status](http://ecam.cmucreatelab.org/status)
    - Enable SSH with username/password
    - Set username (breathecam) and password
    Do NOT set up wifi for actual install on field machines.  It
    causes interference with the camera connections.

### Install card and boot
    ssh breathecam@<newhostname>
    sudo apt update -y && sudo apt upgrade -y
    git clone --recursive https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
    cd breathecam/Code/pi_cam && cp config_files/breathecam.ini-example config_files/breathecam.ini
    # Customize, eg. set grab interval
    nano config_files/breathecam.ini

### copy to /boot/config.txt
### may not be necessary, depending
dtoverlay=imx477
dtoverlay=disable-wifi
dtoverlay=disable-bt

### reboot. This seems to take a long time, maybe several reboots
### before comes up on ssh? 
    ./install.py


### Clone Pi card to multiples

It is handy to initialize multiple cards by cloning the card from an existing Pi host which has been set up as above.  This is less labor-intensive than repeating the initialization steps for each host.

You can do this using the rpi-clone script, https://github.com/billw2/rpi-clone.
  rpi-clone sda
will clone the config to the card mounted on sda (the first USB device attached).
  rpi-clone sda -s hosta -L hosta -U
sets the host name to "hosta", sets the volume label to "hosta", and skips some confirm prompts.

I set up a 4-port USB hub attached to a Pi, and put four cards in four USB sd card readers.  These cards will appear as sda, sdb, etc., in the order that you plug them in.  Then you can do:
  rpi-clone sdb -s hostb -L hosta -U
etc., for the four cards.  See tools/clone.sh

One advantage of rpi-clone is that it uses rsync to transfer files, so if the modification is small it will go much faster than a full bit-copy.  rpi-clone is not set up to run parallel instances (a fixed mount point, for one thing), but you can script multiple sequential runs.

The goal is to have the install.py script set up an configuration which is actually necessary for the breathecam software to run, or for remote access.  This insures that we can easily create a functional system from scratch. But there are various minor things like git environment options, emacs, etc., which give a desirable environment, and it isn't necessary to figure out what all these things are and how to script their configuration.


### Per host configuration (ZeroTier)

Currently the only per-host config setting the zerotier identity.  Run tools/zerotier_add.py on the host to be configured.  On the ZeroTier web site, enable display of unconfigured breathecam hosts.  When the new one appears, give it a suitable name and enable it.  zerotier_add.py will delay until you add the host, looping until it is successful.


### Disabling startup on boot

You can inhibit the boot-time startup by creating the file:
    breathecam/Code/pi_cam/config_files/run_inhibit

This is useful for starting up cloned systems that you may not want to run right away.
This will stop the watchdog behavior from rebooting the system if the cameras are not running (or if the watchdog is berserk).  You can do this remotely by eg.
    ssh host.local "touch breathecam/Code/pi_cam/config_files/run_inhibit"

Even if you have a 1-2 second window before reboot, you can try this multiple times until it works.

An alternate method is to remove the crontab entry:
    ssh host.local "echo '' | sudo crontab -"


### Misc commands/notes:

Each Pi4b board has several LEDs:

* Tiny red LED:  Should be on and solid to indicate good power.  If flashing, indicates insufficient power.
* Tiny green LED:  flashes when accessing SD card
* Large green LEDs on ethernet:  flashes when uploading images


Setting up typescript compilation for webConsole.ts:

[This done automatically by install.py]
Install node and npm:
    sudo apt install nodejs npm

After git clone:
    npm i

First time (remove this section later):
    npm install typescript --save-dev



### Remote access:

We are currently using ZeroTier.  This is installed and configured by tools/zerotier_join.py. 
________________________________________________________________
On any Linux machine, it can be installed via:

    curl -s https://install.zerotier.com | sudo bash

And then to join the network run the following command:

    sudo zerotier-cli join db64858fedb73ddd

At that point, I will have to log into the admin controls and approve the
device. You will also need to install the client software on whatever machine
you plan to use to ssh into the embedded device(s). I'll also need to approve
that machine. You'll use the same network ID (db64...) above. Mac/PC will have
a GUI to plug the numbers into.

Once it's installed on the linux device and on your laptop, I can give you the
specific "local" IP of the linux device to connect. It'll be of the form:
10.147.20.X
________________________________________________________________


To reset the ZeroTier identity after a disk/CF clone, do:
    sudo service zerotier-one stop
    sudo rm /var/lib/zerotier-one/identity.*
    sudo service zerotier-one start

Likewise, if you want to keep an existing identity after a reinstall,
you can copy the old identity.* to the new card.

On a host where ZeroTier is installed and configured for the breathecam net you should be able to access a host by hostname.local.


VNC access:

[The settings described here are done automatically by install.py]

There are various ways that VNC could presumably work, but I tried a number of things that didn't.  

What does work:

Use raspi-config in a terminal or the graphical version from the start menu,
and enable "VNC" in interfaces.  This will set up so you can VNC connect on
the :0 display.  Do not set the system to boot to command prompt, since the
VNC session will not start on :0, and you will get a black screen with
"currently unable to show the desktop".

I also set it to not auto-login.  With these settings (VNC enabled, boot to
desktop, no auto login), if you start headless, then it will not start all of
the desktop stuff until you VNC connect and log in.  Not sure if it is
actually running "virtual" or not.  Possibly resource usage by the VNC session
could affect operation.


Camera setup:

In the field you can check that the camera is working, and the camera aiming,
using the e-cam status page.

The lenses should be pre-focused on a distant subject before taking the camera
out for installation.  This works best using a small ROI (region of interest)
with the libcamera-still preview mode, since this gives a high magnification
and update rate.
    libcamera-still -t 0 --roi 0.5,0.5,0.1,0.1
or
    libcamera-still -t 0 --roi 0.5,0.5,0.1,0.1 --qt-preview

This gives) a 10x zoom (0.1) at the middle of the frame (0.5).  You
can move the ROI if needed.  Adding --qt-preview gives a smaller
window which will update faster over a VNC connection.  --qt-preview
may also work when the default display doesn't.
