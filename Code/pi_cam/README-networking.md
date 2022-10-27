
On "gadget" side:

Bulleye, Sept 22 release







config.txt:
    dtoverlay=dwc2

cmdline.txt
    modules-load=dwc2,g_ether


gadget side:

    sudo modprobe g_ether dev_addr=12:34:56:78:9a:bc host_addr=12:34:56:78:9a:bd

host side:
ifconfig usb0 192.168.97.101 netmask 255.255.255.0


##########

from https://howchoo.com/pi/raspberry-pi-gadget-mode

appended modules_load dwc2,g_ether to /boot/cmdline.txt

appended dtoverlay=dwc2 to /boot/config.txt
