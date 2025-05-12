# Pi configuration and administration

## Create Pi OS image with Raspberry Pi Imager
- Download imager, install and run. (Run as adminstrator under windows or it
  may not be able to reformat the SD card..)
- Select 64-bit pi OS, board pi4
- Click on EDIT SETTINGS and fill in General tab:
    - When using card cloning the build device hostname is "bcinit"
    - Set username (breathecam) and password
    - Do NOT set up wifi for actual install on field machines.  It
      causes interference with the camera connections. Disabling wifi on
      bcinit avoids this problem.
    - Set the country/locale
- Services tab:
    - Enable SSH with password authentication, this will enable ssh login
      for the breathecam user.
- Click NEXT and YES to "apply OS customization".
## Install card into pi and boot
For SSH to work during the next step (before zerotier is installed) you need to be in a net environment where eg. bcinit.local will resolve correctly.  This requires you to be behind some sort of NAT router, and it is up to details of the router to decide to serve that name.  You may need to mess with the router menus to find what it decided to call it.  My router will also accept just "bcinit". If bcinit.local previously existed with a different ethernet address then this may also cause problems with caching on your gateway or local host. 
- Note that if you have zerotier on your local host then this also uses foo.local names, but probably any actual local names will take priority.
- Note that if you have configured a host as the "clock" (see NTP config below) then its .local name is changed to breathecam_ntp.local, not eg. cam1a.local.
If you can't get ssh to work initially you can always plug in monitor, keyboard and mouse and log in that way.

```
ssh breathecam@bcinit.local
sudo apt update -y && sudo apt upgrade -y
git clone --recursive https://github.com/CMU-CREATE-Lab/breathecam_v4.git breathecam
cd breathecam/Code/pi_cam && cp config_files/breathecam.ini-example config_files/breathecam.ini
# Customize, eg. set grab interval
#nano config_files/breathecam.ini
```
You can set the wireless country using raspi-config so login won't nag you, but you don't actually need this if wifi is disabled.

Reboot. Sometimes this takes a while, maybe several reboots before comes up on ssh?
```
cd breathecam/Code/pi_cam
./tools/install.py
```
## Host naming
Cameras are named according to location, camera number, and board.  An example is clairton3a.  This is the "a" camera board in the 3 camera at clairton.  Mostly we have used the camera number to identify different builds installed at the same site, so we might roll out clairton3 while clairton2 is still running, in case there is an issue with the new camera.  In a quad camera the boards are a, b, c, d.  In a 4x1 camera array "a" is the rightmost view from the camera perspective.  See tools/run_quad which will run a command on all four boards.

## Cloning SD cards
It is handy to initialize multiple cards by cloning the card from an existing Pi host which has been set up as above.  This is less labor-intensive than repeating the initialization steps for each host.  See tools/clone.sh, details below.

The goal is to have the install.py script set up a configuration which is actually necessary for the breathecam software to run, or for remote access.  This insures that we can easily create a functional system from scratch. But there are various minor things like git environment options, emacs, etc., which give a desirable environment, and it isn't necessary to figure out what all these things are and how to script their configuration.

Set up a 4-port USB hub attached to a Pi (bcinit.local), and put four cards in four USB sd card readers.  These cards will appear as sda, sdb, etc., in the order that you plug them in.  Then you can do:
  tools/clone.sh host1
to initialize cards for hosts host1a, host1b, host1c, host1d

Before doing this, do:
  tools/kill_all.sh
  rm logs/* image/*.jpg
  touch config_files/run_inhibit
This cleans up any current breathecam outputs and makes sure the clone images won't try to run until they are fully configured.

### Install rpi-clone
clone.sh uses the rpi-clone script, https://github.com/geerlingguy/rpi-clone. You can install this by:
```
curl https://raw.githubusercontent.com/geerlingguy/rpi-clone/master/install | sudo bash
```
If you want to clone just one card you can use rpi-clone directly. This will clone the r8unning system to the card mounted on sda (the first USB device attached):
```
sudo rpi-clone sda
```

Usually you will want to do what clone.sh does, set the host name to "hosta", set the volume label to "hosta", and skip some confirm prompts:
```
  sudo rpi-clone sda -s hosta -L hosta -U
```

One advantage of rpi-clone is that it uses rsync to transfer files, so if the modification is small it will go much faster than a full bit-copy.  clone.sh doesn't run parallel instances because rpi-clone can't handle that (a fixed mount point, for one thing.)

### Clone procedure

Set up a 4-port USB hub attached to bcinit.local. Physically label four USB SD card *readers* A, B, C, D. Physically label four SD *cards* A, B, C, D and install them into the readers, but *do not* insert the card readers into the USB hub yet.

Do this *before* inserting the card readers with the SD cards to be cloned:
```
# stop SD cards from getting auto mounted, which can cause various problems.
sudo systemctl stop udisks2.service
# Clean up any current breathecam outputs
tools/kill_all.sh
rm -f logs/* image/*.jpg
# make sure the clone images won't try to run until they are fully configured.
touch config_files/run_inhibit
```
Insert the SD card readers into the hub *in order*, since the cards will appear as sda, sdb, etc., in the order that you plug them in.  Then clone.sh can clone cards for hosts host1a, host1b, host1c, host1d:
```
tools/clone.sh host1
```
## Per host configuration (ZeroTier)
 Boot the host to be configured and run tools/zerotier_add.py on that host.  On the ZeroTier web site, enable display of unconfigured breathecam hosts.  When the new one appears, give it a suitable name and enable it.  zerotier_add.py will delay until you add the host, looping until it is successful. 
 
 zerotier_join.py also does ssh-keygen to generate a new host ssh key so that all the hosts don't have the same key, which would cause ssh to complain.
## Disabling startup on boot
You can inhibit the boot-time startup of breathecam by creating the file run_inhibit:
```
touch config_files/run_inhibit
```

This is useful for starting up cloned systems that you may not want to run right away. Note that this inhibits a manual call to run_all.sh also.

run_inhibit will prevent a reboot loop by the watchdog in the case where image capture is not working for some reason.  Or maybe the system crashes immediately due to a camera driver problem or something. You can set run_inhibit remotely by:
```
ssh breathecam@host.local "touch breathecam/Code/pi_cam/config_files/run_inhibit"
```
Even if you have a 1-2 second window before reboot, you can try this multiple times until it works.

An alternate method is to remove the crontab entry:
```
ssh breathecam@host.local "echo | sudo crontab -"
```
## Misc commands/notes:
Each Pi4b board has several LEDs:

* Tiny red LED:  Should be on and solid to indicate good power.  If flashing, indicates insufficient power.
* Tiny green LED:  flashes when accessing SD card
* Large green LEDs on ethernet:  flashes when uploading images (or other net activity)
## Remote access:
We are currently using ZeroTier.  This is installed and configured on the pi boards by tools/zerotier_join.py (see per-host configuration above.) On a host where ZeroTier is installed and configured for the breathecam net you should be able to access a host by hostname.local.

For the machine that you connect *from* you will also need to install and configure the zerotier client.  This can be windows or mac as well as linux.  On any Linux machine, it can be installed via:
```
curl -s https://install.zerotier.com | sudo bash
```

And then to join the network run the following command:
```
sudo zerotier-cli join db64858fedb73ddd
```

Log into the zerotier web console and add this host in the same way as for the pi. You'll use the same network ID (db64...) above.

To reset the ZeroTier identity after a disk/CF clone, do:
```
sudo service zerotier-one stop
sudo rm /var/lib/zerotier-one/identity.*
sudo service zerotier-one start
```
Likewise, if you want to keep an existing identity after a reinstall, you can copy the old identity.* to the new card.
### VNC access
\[The settings described here are done automatically by install.py\]

There are various ways that VNC could presumably work, but I tried a number of things that didn't. **This only seems to work using the legacy X11 mode** 

**What does work:**
Use raspi-config in a terminal or the graphical version from the start menu, and enable "VNC" in interfaces.  This will set up so you can VNC connect on the :0 display.  Do not set the system to boot to command prompt, since the VNC session will not start on :0, and you will get a black screen with "currently unable to show the desktop".

I also set it to not auto-login.  With these settings (VNC enabled, boot to desktop, no auto login), if you start headless, then it will not start all of the desktop stuff until you VNC connect and log in.  Not sure if it is actually running "virtual" or not.  Once started, resource usage by the VNC session could possibly affect breathecam operation.
## Camera testing and Webconsole:
In the field you can check that the camera is working and that it is aimed well by using the [e-cam status page](http://ecam.cmucreatelab.org/status)

You can also use the "webconsole", point your browser to to: 
```
http://<pihost>:8000
```
This is easier with a laptop with zerotier where you can connect to eg. clairton3.local. There is also a mobile app that seems to work, but you have to look up the IP address on the zerotier web site, it doesn't support hostname.local.

Webconsole has three modes on selected by bottons. "Zoom out" and "Slow focus view" show the latest image captured at the usual configured frame rate (typically 3 seconds.)  The "Slow focus view" shows a zoomed in view that you can pan around in.  In "Fast focus view" we show a 3x3 array of zoomed parts of the image at the corners and middles. This runs at about 2 FPS but stops normal capturing. Fast focus mode will time out after a while so that normal capture resumes.

The lenses should be pre-focused on a distant subject before taking the camera out for installation.  You can do this using Webconsole or VNC. 
### Focusing using VNC
Connect using VNC and then use the libcamera-still preview.  On VNC it is pretty much necessary to use the --qt-preview option to libcamera-still, which changes to a smaller window with different update method. The default preview sometimes kind of works on VNC, but bogs down badly.

Focusing works best using a small ROI (region of interest) with the libcamera-still preview mode, since this gives a high magnification and update rate.
    libcamera-still -t 0 --roi 0.5,0.5,0.1,0.1 --qt-preview
This gives) a 10x zoom (0.1) at the middle of the frame (0.5).

or for full resolution:
    libcamera-still -t 0 --qt-preview --viewfinder-mode 4056:3040:8 --roi 0.5,0.5,0.05,0.05

You can move the ROI if needed.

## Realtime clock and NTP config

We have multiple Raspberry Pi boards on the same local network. One board, called "clock," is equipped with a battery-backed hardware clock (DS3231). The other boards, called "clients," have no hardware clock. This setup ensures that all boards keep accurate time even if there is no internet or if the router is down.

Currently we put the clock on the "a" host, and the other hosts are clients.  See \*.conf config files in config-files/ directory. These are copied to /etc directories to override system defaults.

#### Clock host:
On the clock host, after we have gotten NTP off the internet initialize the realtime clock:
```
sudo hwclock -w
```

## Time Distribution Scheme Overview

### 1. Failure Modes and Goals

We want to handle:

1. **Internet Uplink Fails**: The router may still give out IP addresses (DHCP), but there's no external connectivity. Clients still need accurate time for logging.
2. **Router or DHCP Fails**: The boards can still talk on the local network (switch or direct), but the router is offline. The "clients" must still get time from "clock."
3. **Partial Board Failures**: If a single "client" fails, the others continue syncing from "clock" or from the internet if available.

In all cases, the "clock" board's DS3231 acts as a reliable local time source.

### 2. Services and Components

1. **Hardware Clock (DS3231)** on the "clock" board  
   - Battery-backed, so it keeps time even when powered off.  
   - Enabled via an "i2c-rtc" overlay (for example, `dtoverlay=i2c-rtc,ds3231` in `/boot/config.txt`).

2. **NTP Daemon (NTPsec or classic ntpd)**  
   - "clock" uses the hardware clock as a fallback ("local clock driver" or by reading the DS3231 at boot).  
   - "clients" reference "clock" plus any public NTP pools when available.

3. **Avahi (mDNS)**  
   - Allows the "clients" to find "clock" by a .local name, e.g. "breathecam_ntp.local," even if the router or DNS is absent.  
   - Each client uses `server breathecam_ntp.local` in ntp.conf.

4. **Syncing Hardware Clock**  
   - A periodic script writes system time (disciplined by NTP) back to the hardware clock via `hwclock -w`.  
   - Ensures the DS3231 remains accurate if the system shuts down unexpectedly.

### 3. Overall Flow

1. **"clock" Board Boot**  
   - Reads DS3231 time on startup (for example, `hwclock -s`).  
   - NTP references both the public NTP pool (if internet is up) and a local clock fallback (for example, `server 127.127.1.0 stratum 10`).  
   - If there's no internet, it still has valid time from DS3231.

2. **"client" Boards Boot**  
   - No battery-backed time, so they start at an arbitrary clock.  
   - NTP tries to sync from "clock" at "breathecam_ntp.local" (via Avahi).  
   - If the internet is up, they also use public pool servers. Otherwise, they rely solely on "clock."

3. **Avahi**  
   - "clock" board is configured in `/etc/avahi/avahi-daemon.conf`, setting `host-name=breathecam_ntp`.  
   - "clients" can always resolve "breathecam_ntp.local" using mDNS, even with no router or DHCP.

4. **Syncing DS3231**  
   - A cron job or systemd timer on "clock" calls `hwclock --systohc` once per day (or at shutdown).  
   - If NTP has improved system time, the DS3231 remains accurate for future reboots.

### 4. Key Config Highlights

#### 4.1 "clock" Board (with DS3231)

- **RTC Overlay** (in `/boot/config.txt`):  
  ```
  dtoverlay=i2c-rtc,ds3231
  ```
- **NTP Fallback** (snippet in `ntp.conf` or similar):
  ```
  pool 0.debian.pool.ntp.org iburst
  server 127.127.1.0
  fudge 127.127.1.0 stratum 10
  tos minclock 1 minsane 1
  ```
  That means:
  - Use the public pool if available.  
  - Fallback to local clock driver at stratum 10.  
  - Accept only one source as "enough."

- **Avahi** (`/etc/avahi/avahi-daemon.conf`):
  ```
  [server]
  host-name=breathecam_ntp
  ```
  This publishes `breathecam_ntp.local`.

- **Sync RTC** (for example, a daily cron job):
  ```
  0 0 * * * /sbin/hwclock --systohc
  ```

#### 4.2 "client" Boards

- **NTP**:
  ```
  server breathecam_ntp.local iburst prefer
  pool 0.debian.pool.ntp.org iburst
  tos minclock 1 minsane 1
  ```
  This ensures that if "breathecam_ntp.local" is reachable, they lock onto it, but they also use the public pool when available.

- **Avahi**:
  - Generally left at defaults so they can do mDNS lookups of "breathecam_ntp.local."

### 5. "No Router" or "No Internet"

1. **No Internet**  
   - "clock" is still valid via DS3231 or local clock driver.  
   - "clients" use Avahi to find "clock" on the LAN.  
   - Everyone remains in sync.

2. **No Router or DHCP**  
   - Pi boards might get link-local addresses (169.254.x.x).  
   - Avahi still works over multicast, so "breathecam_ntp.local" resolves.  
   - Clients sync time from "clock."

3. **Partial Failures**  
   - A single "client" can fail without affecting others.  
   - As long as "clock" stays up, the network has a valid time source.

### 6. Summary

This arrangement allows robust time distribution among a group of Raspberry Pi boards:

- One board ("clock") has the DS3231 hardware clock and runs NTP with a fallback local clock driver.  
- All other boards ("clients") point to "breathecam_ntp.local" plus an NTP pool for internet time if available.  
- Avahi ensures local name resolution works even if the router or DNS is down.  
- The DS3231 is periodically updated via `hwclock -w` so it remains accurate if power is lost.  

As a result, the system provides valid timestamps for image logging or other tasks, regardless of network or router failures.
