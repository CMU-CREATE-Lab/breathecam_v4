#!/usr/bin/env python3
# Wait for the first NTP packet so that we have some sort of vaguely accurate time
# before proceeding. Similar to ntpwait, but we have a much lower threshold for success. 
# If there is no packet in 20 seconds but we do have a realtime clock, then we also return. 
# This way we can call it on the clock host without causing it to hang when there is no net.
# If we wait for normal NTP convergence then we would delay our startup by 5-10 minutes, which
# is annoyingly slow, especially for field testing.
#
# We will wait forever on the client boards if the clock NTP server is inaccessible. 
# See README.md for discussion of the local NTP synch to the RTC.

import subprocess
import time
import os

def has_hardware_rtc() -> bool:
    for path in ("/dev/rtc0", "/dev/rtc"):
        if os.path.exists(path):
            return True
    return False

have_rtc = has_hardware_rtc()
start = time.monotonic()
tries = 0

# The "leap" bits notionally have to do with leap second processing, but also indicate whether
# we've gotten at least one packet.
print("Waiting for network time ", end="", flush=True)
while True:
    try:
        out = subprocess.check_output(
            ["ntpq", "-c", "rv 0 leap"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        if "leap=0" in out or "leap=1" in out:
            break
    except subprocess.SubprocessError:
        pass

    # fallback to RTC after 20 s if present
    if have_rtc and time.monotonic() - start > 20:
        print(" falling back to hardware RTC.", end="", flush=True)
        break

    tries += 1
    time.sleep(2)
    print(".", end="", flush=True)

print(" done.")
