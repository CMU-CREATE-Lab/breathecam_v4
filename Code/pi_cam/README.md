# RPI SETUP

### Create raspbian image with Raspberry Pi Imager

- Select 32-bit raspbian

- Click on Advanced options and fill in
    - Set hostname (e.g. piquad3a or clairton3c)
    - Enable SSH with username/password
    - Set username (breathecam) and password
    - Configure wifi (”wireless LAN”) to connect to your local network
    - Wireless LAN country: US
    - Set locale settings: time zone America/New_York, keyboard US

### Install card and boot

    ssh breathecam@<newhostname>
    git clone --recursive https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
    cd breathecam/Code/pi_cam && cp config_files/breathecam.ini-example config_files/breathecam.ini
    # Customize
    nano config_files/breathecam.ini
    ./install.py

# Remotely disable startup on boot

If you're having a problem where the system fails soon after boot and is rapid-cycle rebooting, consider trying to get back control of it by remotely disabling startup.  Even if you have a 1-2 second window before reboot, you can try this multiple times until it works.

    ssh piquad3a.local "echo '' | sudo crontab -"



### Setting up typescript compilation for webConsole.ts

Install node and npm:

    sudo apt install nodejs npm

After git clone:

    npm i

First time (remove this section later):

    npm install typescript --save-dev





------------------------

- install raspbian (download from https://www.raspberrypi.org/)
  Set hostname to camera id
        [cameraname][elementname]
        e.g. piquad3b where piquad3 is cameraname, and b is the elementname (a being “primary”)
  Current camera names for ecam: [http://ecam.cmucreatelab.org/status](http://ecam.cmucreatelab.org/status)
  - nikonCamera**N**: Nikon cameras
  - piquad**N**: New generation pi “quad” cameras
  
  NOTE: Arducam may require a specific patched kernel distribution, see below.
- update and upgrade and install dependencies
	> sudo apt-get update
	> sudo apt-get upgrade
    > sudo apt install libfmt-dev libboost-program-options-dev libcamera-dev libjpeg62-turbo-dev libexif-dev emacs
- remove GUI (allow to reboot)
	> sudo raspi-config
	  Settings:
	    Interfaces/enable VNC
	    System/boot to desktop, auto login off
	    Can set VNC display resolution to eg. 1280x1024
	    Set hostname? xxx.breathecam.local
	    Can set up wifi for debugging
	> sudo reboot
- git clone https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
- changing hostname (if necessary)
    > sudo hostnamectl set-hostname NEWHOSTNAME --static
    > sudo emacs /etc/hosts
- build
    > cd breathecam/Code/pi_cam_grab
    > make
- cd to rpi code tree
     	> cd breathecam/Code/pi_cam
- launch breathecam on boot
	> sudo crontab -e	(add following to the bottom)
		@reboot /home/breathecam/breathecam/Code/pi_cam/run_all.sh
- per-host config, see below
- reboot and test
	> sudo reboot

Each Pi4b board has several LEDs:

* Tiny red LED:  Should be on and solid to indicate good power.  If flashing, indicates insufficient power.
* Tiny green LED:  flashes when accessing SD card
* Large green LEDs on ethernet:  flashes when uploading images

Kernel and firmware:

There seem to be some issues with the new libcamera-based interfaces.  These
are now standard, and are also being used in some form by Arducam.

Some special configuration may be needed for Arducam:
 -- For the 18 MP Arducam camera I had to use a specific system binary
    distribution (recompiling the kernel is also supposed to work).
 -- For the the Arducam mini HQ-camera I found that I had to:
        sudo rpi-update
    This updates to the latest dev kernel, and also updates the
    video firmware.  This camera seems not to be identical to the official
    Raspberry Pi HQ camera, even though it uses the same sensor.
    Also see boot_config.txt for "ram" config.txt patches in video
    config. camera_auto_detect is off, some dtoverlay needed.
 -- For the "Arducam multi-camera adapter board V2.2" the i2c_vc=on is
    needed, this enables an i2c port on the media controller. Regular
    i2c and the camera interfaces are also enabled, but that already
    seems to be the default.


Arducam multi-camera adapter B012001 (multiplexer):

This switches between four cameras at a pretty low level. Whichever
camera is selected then appears as camera 0 for libcamera-still, etc.

See:
    https://www.arducam.com/docs/cameras-for-raspberry-pi/multi-camera-adapter-board/multi-camera-adapter-board-v2-1/
But you don't need any of their code or suggested installs except to
run their demos (not sure about wiringpi).


Per-host config and SD copying:

Except for per-host config much of this setup can be gotten by copying the SD
card: "Start/Accessories/SD card copier".  This config is per-host and needs
to be repeated:
 -- edit breathecam/Code/pi_cam/config_files/breathecam.ini to set "camera_id"
 -- install remote access, see below.


Remote access:

We are currently using ZeroTier. Paul Dille says:
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

I added my ZeroTier IP to /etc/hosts as test.breathecam.local, etc.  On
windows this is: 
    c:\windows\system32\drivers\etc\hosts

We may want to set this as the DNS hostname in raspi-config.  Or maybe
not.  If we have a different local name, then we can access it by name
on the local net (not using ZeroTier).


VNC access:

It is possible that the GUI may be competing with the camera image capture for
kernel DMA memory.  I've seen failures to allocate DMA "cma" memory.

I tried figuring out how to get VNC access working without starting the
"lxsession" desktop by default, and using "vncserver -virtual", but haven't
been able to get that to work.  Trying just vncserver-virtual after ssh in
resulted in a usable display on :1, but there was no window manager or
taskbar.  In principle you can just start those somehow, but I didn't get that
to work.  See breathecam/Code/pi_cam/startvnc script.

INSTEAD: use raspi-config in a terminal or the graphical version from
the start menu, and enable "VNC" in interfaces.  This is the normal
thing, and will create a :0 display.  Do not set the system to boot to
command prompt, since the VNC session will not start on :0, and you
will get a black screen with "currently unable to show the desktop".

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
    libcamera-still -t 0 --roi 0.1,0.1,0.5,0.5

This gives (maybe) a 10x zoom (0.1) at the middle of the frame (0.5).  You can
move the ROI if needed.  Zoom is "maybe" because there seems to be a limit to
the smallest ROI.  Adding --qt-preview gives a smaller window which will
update faster over a VNC conncetion.  --qt-preview may also work when the
default display doesn't.


TODO:
 -- Watchdog for capture failing does not work with multi-camera when
    at least one camera is working.
