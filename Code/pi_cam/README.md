# RPI SETUP
  Set hostname to camera id

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


# Remotely disabling startup on boot

If you're having a problem where the system fails soon after boot and is rapid-cycle rebooting, consider trying to get back control of it by remotely disabling startup.  Even if you have a 1-2 second window before reboot, you can try this multiple times until it works.

    ssh piquad3a.local "echo '' | sudo crontab -"


### Setting up typescript compilation for webConsole.ts
### [I think this is set up by install.py]
Install node and npm:
    sudo apt install nodejs npm

After git clone:
    npm i

First time (remove this section later):
    npm install typescript --save-dev



### Misc connands/notes:
- > sudo raspi-config
  Settings:
    Interfaces/enable VNC
    System/boot to desktop, auto login off
    Can set VNC display resolution to eg. 1280x1024
    Set hostname? xxx.breathecam.local
    Can set up wifi for debugging
- git clone https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
- changing hostname (if necessary)
    > sudo hostnamectl set-hostname NEWHOSTNAME --static
    > sudo emacs /etc/hosts
- build
    > cd breathecam/Code/pi_cam_grab
    > make
- launch breathecam on boot
	> sudo crontab -e	(add following to the bottom)
		@reboot /home/breathecam/breathecam/Code/pi_cam/run_all.sh

Each Pi4b board has several LEDs:

* Tiny red LED:  Should be on and solid to indicate good power.  If flashing, indicates insufficient power.
* Tiny green LED:  flashes when accessing SD card
* Large green LEDs on ethernet:  flashes when uploading images


### Arducam multi-camera adapter B012001 (multiplexer):
[We are not using this board anymore]
This switches between four cameras at a pretty low level. Whichever
camera is selected then appears as camera 0 for libcamera-still, etc.

See:
    https://www.arducam.com/docs/cameras-for-raspberry-pi/multi-camera-adapter-board/multi-camera-adapter-board-v2-1/
But you don't need any of their code or suggested installs except to
run their demos.

In config.txt, for the "Arducam multi-camera adapter board V2.2"
i2c_vc=on is needed, this enables an i2c port on the media
controller. Regular i2c and the camera interfaces are also enabled,
but that already seems to be the default.


Per-host config and SD copying:

Except for per-host config all of the setup can be gotten by copying
the SD card: "Start/Accessories/SD card copier".  Currently the only
per-host config resetting the zerotier identity.  But startung using
install.py insures that we know how to regenerate the configuration.


Remote access:

We are currently using ZeroTier.
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
    libcamera-still -t 0 --roi 0.5,0.5,0.1,0.1

This gives) a 10x zoom (0.1) at the middle of the frame (0.5).  You
can move the ROI if needed.  Adding --qt-preview gives a smaller
window which will update faster over a VNC connection.  --qt-preview
may also work when the default display doesn't.
