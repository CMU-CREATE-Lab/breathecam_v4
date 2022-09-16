#!/usr/bin/python3

import getpass, os, subprocess

script_dir = os.path.dirname(os.path.realpath(__file__))
username = getpass.getuser()

def shell_cmd(cmd):
    print(cmd)
    print(subprocess.check_output(cmd, shell=True, encoding="utf-8"))

def update_crontab(name, line, username=None):
    username = username or getpass.getuser()
    if username != getpass.getuser():
        sudo = "sudo"
    else:
        sudo = ""
    # Read current 
    cmd = f"{sudo} crontab -u {username} -l 2>/dev/null"
    completed = subprocess.run(cmd, shell=True, capture_output=True, encoding="utf-8")
    assert(completed.returncode == 0)
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

print("Install apt package dependencies")
shell_cmd("sudo apt update")
shell_cmd("sudo apt install -y libcamera0 python3-libcamera libimage-exiftool-perl python3-picamera2")

print("Check kernel version")
kernel_version = subprocess.check_output("uname -r", shell=True, encoding="utf-8").strip()
kernel_version = kernel_version.split("-")[0]
minimum_kernel_version = "5.15.61"

if parse_kernel_version(kernel_version) < parse_kernel_version(minimum_kernel_version):
    msg = f"Require kernel version >= 5.15.61 but have {kernel_version}.  Use sudo apt update && sudo apt upgrade"
    print(msg)
    raise(Exception(msg))


if os.path.exists(os.path.expanduser("~/pi-monitor")):
    print("Updating pi-monitor")
    shell_cmd("~/pi-monitor/update.py")
else:
    print("Installing pi-monitor")
    shell_cmd("cd ~ && git clone --recursive https://github.com/CMU-CREATE-Lab/pi-monitor.git")
    shell_cmd("~/pi-monitor/install.py")


python = "/usr/bin/python3"

update_crontab("pi_cam-reboot", f"@reboot {script_dir}/run_all.sh", username="root")



