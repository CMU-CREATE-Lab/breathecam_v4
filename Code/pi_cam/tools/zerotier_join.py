#!/usr/bin/python3
# This is network initialization required on each host, and which
# needs to be repeated if a host is initialized from a cloned SD card,
# since the device has to have a distinct identity.  This split off
# from install.py because it should *not* be repeated.

import getpass, os, socket, subprocess, sys, time

script_dir = os.path.dirname(os.path.realpath(__file__))
username = getpass.getuser()

def shell_cmd(cmd):
    print(cmd)
    print(subprocess.check_output(cmd, shell=True, encoding="utf-8"))

def zerotier_join_network(network):
    try:
        subprocess.check_output("sudo zerotier-cli listnetworks", shell=True)
    except:
        print("Installing zerotier")
        shell_cmd("curl -s https://install.zerotier.com | sudo bash")

    client_id = subprocess.check_output("sudo zerotier-cli info", shell=True, encoding="utf-8").split()[2]

    while True:
        shell_cmd(f"sudo zerotier-cli join {network}")
        netinfo = subprocess.check_output(f"sudo zerotier-cli listnetworks | grep {network}", shell=True, encoding="utf-8")
        print(netinfo)
        if "ACCESS_DENIED" in netinfo:
            hostname = socket.gethostname()
            url = f"https://my.zerotier.com/network/{network}"
            print(f"zerotier: PLEASE AUTHENTICATE CLIENT {client_id} (hostname {hostname}) for access to network {network} at {url}")
        elif "REQUESTING_CONFIGURATION" in netinfo:
            print("Waiting for response from zerotier server")
        elif "OK" in netinfo:
            print(f"zerotier: joined and authenticated to network {network}")
            return
        else:
            print("Unknown reply from zerotier listnetworks")
        time.sleep(5)

zerotier_join_network("db64858fedb73ddd")

# Generate new SSH host keys since existing one was cloned
shell_cmd("sudo rm -f /etc/ssh/ssh_host_*key*")
shell_cmd("sudo ssh-keygen -A")
shell_cmd("sudo systemctl restart ssh")
