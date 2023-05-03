#!/usr/bin/python3

import os, subprocess

script_dir = os.path.dirname(os.path.realpath(__file__))
os.chdir(script_dir)

def shell_cmd(cmd):
    print(cmd)
    print(subprocess.check_output(cmd, shell=True, encoding="utf-8"))

shell_cmd("git pull --rebase")
subprocess.run("./install.py")
print("update.py DONE")
