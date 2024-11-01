#!/usr/bin/python3

import getpass, os, socket, subprocess, sys, time

script_dir = os.path.realpath(os.path.dirname(os.path.realpath(__file__)) + "/../")
username = getpass.getuser()
debian_release_version = int(subprocess.check_output("lsb_release -rs", shell=True, encoding="utf-8").strip().lower())

def shell_cmd(cmd):
    print(cmd)
    print(subprocess.check_output(cmd, shell=True, encoding="utf-8"))

def install_ssh_key(key):
    keyname = key.split()[-1]
    sshdir = os.path.expanduser("~/.ssh")
    if not os.path.exists(sshdir):
        os.mkdir(sshdir, mode=0o700)
    keyfile = os.path.expanduser("~/.ssh/authorized_keys")
    if os.path.exists(keyfile):
        keyfile_contents = open(keyfile).read()
        if keyfile_contents[-1] != "\n":
            keyfile_contents += "\n"
    else:
        keyfile_contents = ""
    current_keys = [line.strip() for line in keyfile_contents.splitlines()]
    if key in current_keys:
        print(f"Key {keyname} already installed")
    else:
        open(keyfile, "w").write(keyfile_contents + key + "\n")
        print(f"Key {keyname} installed")

def update_crontab(name, line, username=None):
    username = username or getpass.getuser()
    if username != getpass.getuser():
        sudo = "sudo"
    else:
        sudo = ""
    # Read current 
    cmd = f"{sudo} crontab -u {username} -l"
    print(cmd)
    completed = subprocess.run(cmd, shell=True, capture_output=True, encoding="utf-8")
    assert(completed.returncode == 0 or "no crontab for" in completed.stderr)
    prev_crontab = completed.stdout.splitlines(keepends=True)
    token = f"AUTOINSTALLED:{name}"
    installme = f"{line} # {token}"
    old_lines = [line for line in prev_crontab if token in line]
    other_lines = [line for line in prev_crontab if token not in line]
    if len(old_lines) == 1 and old_lines[0].strip() == installme:
        print(f"{name}: already up-to-date in {username} crontab: {installme}")
        return
    elif old_lines:
        print(f"{name}: replacing entry in {username} crontab: {installme}")
    else:
        print(f"{name}: adding entry in {username} crontab: {installme}")
    new_crontab_content = ''.join(other_lines) + installme + "\n"
    cmd = f"{sudo} crontab -u {username} -"
    subprocess.check_output(cmd, shell=True, input=new_crontab_content, encoding="utf-8")

# convert string x.y.z into array of integers [x, y, z]
def parse_kernel_version(version):
    return [int(n) for n in version.split(".")]

config_file = script_dir + "/config_files/breathecam.ini"
if not os.path.exists(config_file):
    msg = f"You must create {config_file} before running install.py.\nYou may copy and modify from breathecam.ini-example."
    print(msg)
    raise Exception(msg)

print("Install apt package dependencies")
shell_cmd("sudo apt update")
# libcam library name seems to have changed starting in Debian Bookworm (12)
if debian_release_version > 11:
    shell_cmd("sudo apt install -y libcamera0.1 python3-libcamera libimage-exiftool-perl python3-picamera2 npm")
else:
    shell_cmd("sudo apt install -y libcamera0 python3-libcamera libimage-exiftool-perl python3-picamera2 npm")

# user for local time server from realtime clock in case net is down
shell_cmd("sudo apt install -y ntp")

print("Installing python3-flask from apt")
shell_cmd(f"sudo apt install -y python3-flask")

# gunicorn is used as the flask server   
shell_cmd(f"sudo apt-get install -y gunicorn")

    
print("Check kernel version")
kernel_version = subprocess.check_output("uname -r", shell=True, encoding="utf-8").strip()
kernel_version = kernel_version.split("-")[0]
minimum_kernel_version = "5.15.61"

if parse_kernel_version(kernel_version) < parse_kernel_version(minimum_kernel_version):
    msg = f"Require kernel version >= 5.15.61 but have {kernel_version}.  Use sudo apt update && sudo apt upgrade"
    print(msg)
    raise(Exception(msg))


def add_line_to_config(line, config_file_path="/boot/config.txt"):
    """
    Adds the specified line to the config file if it's not already present, using sudo to modify the file.

    :param line: The line to add to the config file.
    :param config_file_path: Path to the config file (default is '/boot/config.txt').
    """
    # Read the existing lines in the config file
    with open(config_file_path, "r") as file:
        lines = file.readlines()

    # Check if the line is already present
    if not any(line.strip() in l for l in lines):
        # If not present, append it using sudo and tee
        try:
            subprocess.run(
                ["echo", f"\n{line}\n", "|", "sudo", "tee", "-a", config_file_path],
                check=True,
                text=True,
                shell=True
            )
            print(f'Added "{line}" to {config_file_path}')
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
    else:
        print(f'"{line}" is already present in {config_file_path}')


# Add options to config.txt
# Enable realtime clock (may not actually be present)
add_line_to_config("dtoverlay=i2c-rtc,ds3231")
# Disable wireless stuff because it can interfere with the cameras
# when inside the enclosure (and doesn't work anyway in that case).
add_line_to_config("dtoverlay=disable-wifi")
add_line_to_config("dtoverlay=disable-bt")


if os.path.exists(os.path.expanduser("~/pi-monitor")):
    print("Updating pi-monitor")
    shell_cmd("~/pi-monitor/update.py")
else:
    print("Installing pi-monitor")
    shell_cmd("cd ~ && git clone --recursive https://github.com/CMU-CREATE-Lab/pi-monitor.git")
    shell_cmd("~/pi-monitor/install.py")

python = "/usr/bin/python3"

# We enable to GUI for VNC access, but it doesn't really start unless
# we have a screen or somebody logs in on VNC.  So there is minimal
# overhead when not used.
print("Enable GUI, but require login password")
shell_cmd("sudo raspi-config nonint do_boot_behaviour B3")
# Turn on VNC access.  0 means on, for some reason.
shell_cmd("sudo raspi-config nonint do_vnc 0")

# Node and typescript
print("Installing/updating node dependencies (e.g. typescript compiler)")
shell_cmd("npm i")

# Randy's public key
install_ssh_key("ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1MjEAAACFBAHTlbKK+xkcgmCPGayAtRaEeisB+zbaaPUtz4hCi9jJIZP9PGTtqYNN/3DYzoegBerYx7It7jLaj1PnBqGkZdWIwgCpFOFJRvjf0qQU0IPFAyceV83Jj4cqTj6Xey3LmgLcNRuv3YeX2eIf+8QKrwy+rWUS3mIfQsWWGDrioCc6VDFSaw== rsargent@MacBook-Pro-94.local")

# Rob's public key
install_ssh_key("ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDUHHQOuxYvVWOewo5a9c5h6577SoJUsWaDgJU2quNWYaqcFvXgdnsaT3sFD3KcFeBPnwxQsVM2DROyWMlnk9zKvOc9/tNs9dlswZfM03FhD1ODUzBErnQS4YpRLvehXE/BTIU9dRq0SsBNLhdRFmr7u3bWu9rvNI1Euf4VWLLJxEVTyMbq08U4OhgDVY+aYQ3NpCuDSEAT2YDnaDDcXpvfODh+/jCVsYwj48UEpZD99hcabNM6Ww20D8Ru/8gCt88GkdGgvwPQe7KXKgHCF82iEhU+JlZisVvtqylFP2niXFrUWYIRCHaPnQEeia4sHN37vHcrGCy98I0Crw1Ek6kH ram@TREMOR")

# Breathecam public key
install_ssh_key("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGYlAWzLCoF5zyYN1IOFoSzsMitBlPCjknZkaHWIK9Yo breathecam@piquad3b")

# Turn off "quiet" and "splash" in /boot/cmdline.txt to show verbose boot messages
print("Enabling verbose text boot messages")
shell_cmd("sudo sed --in-place s/quiet// /boot/cmdline.txt")
shell_cmd("sudo sed --in-place s/splash// /boot/cmdline.txt")


print("Halt breathecam services (if running)")
shell_cmd(f"{script_dir}/tools/kill_all.sh") 
print("Testing image capture")
shell_cmd(f"{python} {script_dir}/imageService.py --test-only")
print("Start breathecam services")
subprocess.run(f"{script_dir}/run_all.sh", shell=True)
time.sleep(5)
update_crontab("pi_cam-reboot", f"@reboot {script_dir}/run_all.sh", username="root")
print("install.py DONE")
