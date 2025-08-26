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
### Install rpi-clone
clone.sh uses the rpi-clone script, https://github.com/geerlingguy/rpi-clone. You can install this by:
```
curl https://raw.githubusercontent.com/geerlingguy/rpi-clone/master/install | sudo bash
```
If you want to clone just one card you can use rpi-clone directly. This will clone the r8unning system to the card mounted on sda (the first USB device attached):
```
sudo rpi-clone sda
```

Usually you will want to do what `clone.sh` does --- set the host name to "hosta", set the volume label to "hosta", and skip some confirm prompts:
```
  sudo rpi-clone sda -s hosta -L hosta -U
```

One advantage of rpi-clone is that it uses rsync to transfer files, so if the modification is small it will go much faster than a full bit-copy.  clone.sh doesn't run parallel instances because rpi-clone can't handle that (a fixed mount point, for one thing.)
### Clone procedure
Set up a 4-port USB hub attached to `bcinit.local`. Physically label four USB SD card *readers* A, B, C, D. Physically label four SD *cards* A, B, C, D and install them into the readers, but *do not* insert the card readers into the USB hub yet.

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

I leave `bcinit.local` unconfigured on Zerotier to avoid host ID confusion after cloning, but if you are cloning from a host that already has Zerotier configured then clear its identity by doing:

```
sudo service zerotier-one stop
sudo rm /var/lib/zerotier-one/identity.*
```
Likewise, if you want to keep an existing identity after a reinstall, you can copy the old identity.* to the new card. 

Insert the SD card readers into the hub *in order*, since the cards will appear as sda, sdb, etc., in the order that you plug them in.  Then `clone.sh` can clone cards for hosts host1a, host1b, host1c, host1d:
```
tools/clone.sh host1
```
## Per host configuration
Boot the new host from a cloned card and ssh to it with eg. `ssh breathecam@host1a`.  Run `tools/zerotier_add.py` on that host.  On the [Zerotier web site](https://my.zerotier.com/network/db64858fedb73ddd), enable display of never-authorized breathecam hosts.  This filter option only appears when there is a new host requesting access. When the new one appears, give it the Pi hostname as its name and authorize it.  `zerotier_add.py` will delay until you add the host, looping until it is successful. 
 
 `zerotier_add.py` also does `ssh-keygen` to generate a new host ssh key so that all the hosts don't have the same key, which causes ssh to complain.

You need additional per-host configuration to get the local NTP time distribution working (as described below.)  Do these after `tools/zerotier_join.py`:

On time server (the "a" host):
```
tools/net_config_clock.sh
```

On time clients (the "bcd" hosts):
```
tools/net_config_client.sh
```

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
We are currently using ZeroTier.  This is installed and configured on the pi boards by `tools/zerotier_join.py` (see per-host configuration above.) On a host where ZeroTier is installed and configured for the breathecam net you should be able to access a host by hostname.local.

For the machine that you connect *from* you will also need to install and configure the zerotier client.  This can be windows or mac as well as linux.  On any Linux machine, it can be installed via:
```
curl -s https://install.zerotier.com | sudo bash
```

And then to join the network run the following command:
```
sudo zerotier-cli join db64858fedb73ddd
```
On windows you use the gui to join somehow.

Log into the  [Zerotier web site](https://my.zerotier.com/network/db64858fedb73ddd) and add this host in the same way as for the pi. You'll use the same network ID (db64...) above.

### Accessing stand-alone for testing using Windows 10 Laptop
Setup up connection sharing for the laptop ethernet port. On the ethernet port adapter, under IPV4 settings, make sure "select address automatically" is set. Windows will then set this to a fixed address when sharing is enabled (eg 192.168.137.1). Go to the  adapter settings for the internet connection (eg. wifi), and in properties, on the sharing tab, enable sharing. Select the laptop ethernet port as the "local network".  Close out the dialogs and reboot the pi.

 You can see if the pi has connected by 'arp -a' in the windows command prompt. It would show up under the 192.168.137.* interface as 192.168.1.137.nnn, where nnn isn't 255. If you are lucky then you should be able to connect via '\<pi name\>.local'. The breathecam 'a' host is typically configured as the NTP server and will respond to 'breathecam_ntp.local' via the avahi daemon, while the 'b-d' hosts  should respond as to 'clairton3b.local' etc.   Also, if you are internet connected, go to Zerotier and see if the host is connected. If the '.local' isn't working you can directly connect to the IP from 'arp -a' or Zerotier.

The 192.168.1.137.1 network will only show up in 'arp -a' if you have connection sharing enabled and the wired connection is live. If you see this network but the pi host doesn't appear, it may work to turn *off* connection sharing (as above), reboot windows, turn connection sharing back on, then power cycle the pi. 

### VNC access
**\[The settings described here are done automatically by install.py\]**

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

Currently we put the clock on the "a" host, and the other hosts are clients.  See `*.conf` config files in `config-files/` directory. Scripts `tools/net_config*.sh` copy these files to `/etc` directories to override system defaults.
### All hosts:
**\[This is being done by tools/net_config_common.sh which is called from install.py]**
This assigns a link local IPV4 address so that Avahi can publish it as .local
```
# 1) normal wired profile (you already have this one)
sudo nmcli connection modify "Wired connection 1" \
        ipv4.method auto \
        ipv4.dhcp-timeout 15 \
        ipv4.may-fail yes \
        connection.autoconnect-priority 0

# 2) EXTRA link-local-only profile with lower priority
sudo nmcli connection add type ethernet ifname eth0 con-name eth0-ll \
        ipv4.method link-local \
        ipv4.may-fail yes \
        connection.autoconnect-priority -20
```

With later versions of netmanager this version is more tasteful and concise, but isn't supported by network manager in Bookworm:

```
 sudo nmcli connection modify "Wired connection 1" \
     ipv4.method auto \
     ipv4.link-local fallback \
     ipv4.dhcp-timeout 15
```

## Time Distribution Scheme Overview

### 1. Failure Modes and Goals

We want to handle:
1. **Internet Uplink Fails**: The router may still give out IP addresses (DHCP), but there's no external connectivity. Clients still need accurate time for logging.
2. **Router or DHCP Fails**: The boards can still talk on the local network (switch or direct), but the router is offline. The "clients" must still get time from "clock."
3. **Partial Board Failures**: If a single "client" fails, the others continue syncing from "clock" or from the internet if available.

So under various failure modes the "clock" board's DS3231 acts as a local time source for all the cards. Note that we only block waiting for NTP on startup. Once the breathecam servers are started they will keep running, network or no.  See ''tools/wait_for_ntp.py''.

#### NTP second order problems:
TLDR: offline operation may come unstuck if not all the cards boot under the same network conditions (DHCP vs link-local.) This isn't likely because normally all cards boot at the same time, when the power comes up. Another way this could happen is if just one host reboots. But so far as we know this uncommon, and would be a double failure of some sort.

NetManager doesn't seem to notice when network goes away, the hosts stay with their last DHCP. Any cards with *do* reboot seem to lose their ability to talk because they don't have an old IP. It seems OK if all the cards reboot. Related, ntp doesn't seem to notice if the clock IP address changes due to switching from DHCP to link-local. So if clock alone reboots when we are running with net down, then clock will come up in link-local mode but the clients are still using their old DHCP. They can't talk to clock. 

Eventually, after 24 hours or so net manager does notice DHCP is gone and enables link-local IP. We can then connect from client to clock, but NTP still keeps using the old IP address. Also, eventually, after 24 hours or so without clock, ntpstat starts reporting not synchronized. But this doesn't really matter because we only use ntpstat to delay startup until we have the time. We don't stop if we lose synch, which is fine I think. We will only run for a week or so without net, and it isn't terrible if the images are bit out of synch, definitely better to keep logging.
### 2. Services and Components

1. **Hardware Clock (DS3231)** on the "clock" board  
   - Battery-backed, so it keeps time even when powered off.  
   - Enabled via an "i2c-rtc" overlay (for example, `dtoverlay=i2c-rtc,ds3231` in `/boot/config.txt`).

2. **NTP Daemon (NTPsec or classic ntpd)**  
   - "clock" uses the hardware clock as a fallback (by reading the DS3231 at boot).  
   - "clients" reference "clock" plus any public NTP pools when available.

3. **Avahi (mDNS)**  
   - Allows the "clients" to find "clock" by a .local name, e.g. "breathecam_ntp.local," even if the router or DNS is absent.  
   - Each client uses `server breathecam_ntp.local` in ntp.conf.
   
4. **Netmanger**
   - Has to be configured to allow fallback to link-local IP assignment if there is no DHCP service, see `tools/net_config_common.sh`.

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

The kernel should automatically synchronize the hardware clock to NTP time once NTP is synchronized.

### 4. Key Config Highlights

#### 4.1 "clock" Board (with DS3231)
- **RTC Overlay** (in `/boot/config.txt`):  
   **\[This is done by `install.py` on all cards]**
  ```
  dtoverlay=i2c-rtc,ds3231
  ```
- **NTP Fallback**: 
   see `config_files/ntp.clock.conf`
  - Use the public pool if available.  
  - Fallback to local clock driver at stratum 10.  
  - Accept only one source as "enough."

- **Avahi**:
   See `config_files/avahi_daemon.clock.conf`
   This publishes `breathecam_ntp.local`.
#### 4.2 "client" Boards
- **NTP**:
  See `config_files/ntp.client.conf`
  - This ensures that if "breathecam_ntp.local" is reachable, they lock onto it, but they also use the public pool when available.

- **Avahi**:
  - left at defaults so they can do mDNS lookups of "breathecam_ntp.local."

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
- link-local IP assignment gives Avahi an IP to distribute.
- The DS3231 is periodically updated by the kernel so it remains accurate.  

As a result, the system provides valid timestamps for image logging or other tasks, regardless of network or router failures.
