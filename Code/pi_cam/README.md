# RPI SETUP

### Create raspbian image with Raspberry Pi Imager
- Download imager, install and run. (Run as adminstrator under windows or it
  may not be able to reformat the SD card..)
- Select 64-bit pi OS, board pi4
- Click on EDIT SETTINGS and fill in
  General tab:
    - When using card cloning the build device hostname is "bcinit"
    - Set username (breathecam) and password
    - Do NOT set up wifi for actual install on field machines.  It
      causes interference with the camera connections. Disabling wifi on
      bcinit avoids this problem.
    - Set the country/locale
  Services tab:
    - Enable SSH with password authentication, this will enable ssh login
      for the breathecam user.
- Click NEXT and YES to "apply OS customization".


### Install card into pi and boot

For SSH to work during the next step (before zerotier is installed) you need to be in a net environment where eg. bcinit.local will resolve correctly.  This requires you to be behind some sort of NAT router, and it is up to details of the router to decide to serve that name.  You may need to mess with the router menus to find what it decided to call it.  If bcinit.local previously existed (which it does in zerotier) then this may also cause problems, maybe you host will try to go thru zerotier, which is not connected anymore.  Maybe your router will serve the name, or maybe it will be confused by the unfamilar vibes.

If you can't get ssh to work initially you can always plug in monitor, keyboard and mouse and log in that way.

You can set the wireless country using raspi-config so login won't nag you, but you don't actually need this if wifi is disabled.

    ssh breathecam@bcinit.local
    sudo apt update -y && sudo apt upgrade -y
    git clone --recursive https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
    cd breathecam/Code/pi_cam && cp config_files/breathecam.ini-example config_files/breathecam.ini
    # Customize, eg. set grab interval
    nano config_files/breathecam.ini

### reboot. This seems to take a long time, maybe several reboots
### before comes up on ssh? 
    cd breathecam/Code/pi_cam
    ./tools/install.py


### Clone bcinit SD card to get the cards to install in cameras

It is handy to initialize multiple cards by cloning the card from an existing Pi host which has been set up as above.  This is less labor-intensive than repeating the initialization steps for each host.  See tools/clone.sh, details below.

The goal is to have the install.py script set up a configuration which is actually necessary for the breathecam software to run, or for remote access.  This insures that we can easily create a functional system from scratch. But there are various minor things like git environment options, emacs, etc., which give a desirable environment, and it isn't necessary to figure out what all these things are and how to script their configuration.

Cameras are named according to location, camera number, and board.  An example is clairton3a.  This is the "a" camera board in the 3 camera at clairton.  Mostly we have used the camera number to identify different builds installed at the same site, so we might roll out clairton3 while clairton2 is still running, in case there is an issue with the new camera.  In a quad camera the boards are a, b, c, d.  In a 4x1 camera array "a" is the rightmost view from the camera perspective.  See tools/run_quad which will run a command on all four boards.

Set up a 4-port USB hub attached to a Pi (bcinit.local), and put four cards in four USB sd card readers.  These cards will appear as sda, sdb, etc., in the order that you plug them in.  Then you can do:
  tools/clone.sh host1
to initialize cards for hosts host1a, host1b, host1c, host1d

Before doing this, do:
  tools/kill_all.sh
  rm logs/* image/*.jpg
  touch config_files/run_inhibit
This cleans up any current breathecam outputs and makes sure the clone images won't try to run until they are fully configured.

clone.sh uses the rpi-clone script, https://github.com/billw2/rpi-clone.
```
	$ git clone https://github.com/billw2/rpi-clone.git 
	$ cd rpi-clone
	$ sudo cp rpi-clone rpi-clone-setup /usr/local/sbin
```

  rpi-clone sda
will clone the config to the card mounted on sda (the first USB device attached).
  rpi-clone sda -s hosta -L hosta -U
sets the host name to "hosta", sets the volume label to "hosta", and skips some confirm prompts.

One advantage of rpi-clone is that it uses rsync to transfer files, so if the modification is small it will go much faster than a full bit-copy.  rpi-clone is not set up to run parallel instances (a fixed mount point, for one thing), but you can script multiple sequential runs.


### Per host configuration (ZeroTier)

Generate new SSH host keys: (zerotier_join.py is doing ssh-keygen, not the rm, IDK)
    sudo rm /etc/ssh/ssh_host*; sudo ssh-keygen -A

Currently the only per-host config setting is the zerotier identity.  Boot the host to be configured and run tools/zerotier_add.py on that host.  On the ZeroTier web site, enable display of unconfigured breathecam hosts.  When the new one appears, give it a suitable name and enable it.  zerotier_add.py will delay until you add the host, looping until it is successful.


### Disabling startup on boot

You can inhibit the boot-time startup by creating the file:
    breathecam/Code/pi_cam/config_files/run_inhibit

This is useful for starting up cloned systems that you may not want to run right away. You should create this on bcinit.local before cloning.

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
you plan to use to ssh into the embedded device(s).  You'll use the same network ID (db64...) above.

For the machine that you connect *from* you will also need to install and configure the zerotier client.  This can be windows or mac as well as linux.  On the zerotier web console adding works in the same way as for the pi.  You will also need to install zerotier and connect, using instructions from zerotier.

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

Use raspi-config in a terminal or the graphical version from the start menu, and enable "VNC" in interfaces.  This will set up so you can VNC connect on the :0 display.  Do not set the system to boot to command prompt, since the VNC session will not start on :0, and you will get a black screen with "currently unable to show the desktop".

I also set it to not auto-login.  With these settings (VNC enabled, boot to
desktop, no auto login), if you start headless, then it will not start all of the desktop stuff until you VNC connect and log in.  Not sure if it is
actually running "virtual" or not.  Possibly resource usage by the VNC session could affect operation.


Camera setup:

In the field you can check that the camera is working, and the camera aiming, using the e-cam status page.  You can also use the "webconsole", point your browser to to: 
    http://<pihost>:8000
This is easier with a laptop with zerotier where you can connect to eg. clairton3.local.  Webconsole has full resolution view with or without a zoom for focusing.  The update rate is pretty low, <1 FPS, but still faster than the usual upload rates of 3 sec or slower.

The lenses should be pre-focused on a distant subject before taking the camera out for installation.  I do this by connecting using VNC and then using the libcamera-still preview.  On VNC it is pretty much necessary to use the --qt-preview option to libcamera-still, which changes to a smaller window with different update method. The default preview sometimes kind of works on VNC, but bogs down badly.

Focusing works best using a small ROI (region of interest) with the libcamera-still preview mode, since this gives a high magnification and update rate.
    libcamera-still -t 0 --roi 0.5,0.5,0.1,0.1 --qt-preview
This gives) a 10x zoom (0.1) at the middle of the frame (0.5).

or for full resolution:
    libcamera-still -t 0 --qt-preview --viewfinder-mode 4056:3040:8 --roi 0.5,0.5,0.05,0.05

You can move the ROI if needed.
