#!/usr/bin/python

# v1 - 09/08/2016

import os
import time
import requests
import glob
import logging
import sys
import traceback
from serviceConfig import ServiceConfig

try:
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

    conf = ServiceConfig('./', 'pingServer')
    log = conf.logger

    pingurl = "http://breathecam.cmucreatelab.org:80/location_pinger"

    uuid = "".join("{:02x}".format(ord(c)) for c in conf.camera_id())
    pingpayload = "id=" + conf.camera_id() + "&uuid=" + uuid

    log.info("id: " + conf.camera_id())
    log.info("pingurl: "+pingurl)
    log.info("pingpayload: "+pingpayload)
    log.info("starting application")

    # If more than this many files backlogged (despite ping success), and backlog
    # is increasing, then upload does not seem to be working. [count]
    backlog_threshold = 10

    # If the oldest image file is older than this, then image capture seems to be
    # failing. [seconds]
    #age_threshold = 120
    age_threshold = 60

    # If watchdog test fails on this many pings then something is wrong, and we
    # should exit to force a reboot. [minutes]
    #watchdog_threshold = 10
    watchdog_threshold = 5

    # Previous number of backlog images
    prev_backlog = []

    # Number of times which ping succeeded but the watchdog test failed.
    failures = 0

    while True:
        # Waiting first means we probably have a new image before we find the
        # image age, which prevents a spurious watchdog detect on startup.  (This
        # would be harmless in any case, since we need watchdog_threshold
        # consecutive failures before we reboot).
        time.sleep(60)

        success = False
        try:
            log.debug("Sending ping to server")

            r = requests.post(pingurl, data=pingpayload, timeout = 10)
            response2 = str(r.json)
            if (response2.find("200") > 0):
                log.info("Got a 200 from server, ping successful")
                success = True
            else:
                log.warning("Bad response from server, ping failed: "
                            + response2)

        except:
            log.error("Unexpected error: "+str(sys.exc_info()[0]))


        # This is our watchdog code.  If we are pinging, but 
        # we are not getting any new images (image capture failing)
        # on watchdog_threshold consecutive pings,
        # then we exit, which causes a reboot in the launcher script.
        #
        # One fault that we *don't* deal with is that network access might
        # be failing in a way that would be recovered by reboot.  Probably
        # we should cover this, but one downside is that if there is no
        # network then we can't capture images for later upload because we
        # don't know the time.

        if success:
            last_cap_filename = f"{conf.image_dir()}/last_capture.timestamp"
            try:
                last_cap_timestamp = os.path.getmtime(last_cap_filename)
            except:
                last_cap_timestamp = 0
            age = time.time() - last_cap_timestamp
            if age > age_threshold:
                log.info(f"BAD: MOST RECENT CAPTURE IS TOO OLD ({age:.0f} seconds > {age_threshold} seconds)")
                failures += 1
                log.warning("%d successive watchdog failures", failures)
            else:
                log.info(f"GOOD: Most recent capture is new ({age:.0f} seconds <== {age_threshold} seconds)")
                failures = 0
                
            if (failures >= watchdog_threshold):
                log.error("Repeated watchdog test failure, exiting to force reboot")
                exit()
except Exception as e:
    # really any error
    log.error(f"Unexpected error, waiting 60 seconds before exiting: {repr(e)}")
    log.error(traceback.format_exc())
    time.sleep(60.0)
    raise
