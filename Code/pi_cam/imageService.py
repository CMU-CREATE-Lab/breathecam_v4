import datetime
import math
import shutil
import subprocess
import sys
from shutil import disk_usage
import time
import logging
from serviceConfig import ServiceConfig
import os
from picamera2 import Picamera2
import libcamera
from os.path import exists
import ArducamMux

class ImageService:
    def __init__(self, config: ServiceConfig, test_only=False):
        self.config = config
        self.test_only = test_only
        self.log = config.logger
        self.last_grab = 0
        bc = config.parser["breathecam"]
        self.camera_mux = int(bc["camera_mux"])
        self.mux_channels = [int(x) for x in bc["mux_channels"].split()]
        self.rotation = [int(x) for x in bc["rotation"].split()]
        # tuning_file path is relative to the directory of this script
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.tuning_file = os.path.join(script_dir, bc["tuning_file"])
        self.interval = int(bc["interval"]) # in seconds

    def checkDiskUsage(self):
        wot = disk_usage(self.config.base_dir())
        return wot.used / wot.total

    def grabLoop(self):
        self.log.info(f"Instantiating Picamera2 with tuning file {self.tuning_file}")
        picam2 = Picamera2(tuning=self.tuning_file)
        transform = libcamera.Transform(rotation=self.rotation[0])

        # preview defaults to lower resolution, auto-exposure and auto-white-balance
        preview_config = picam2.create_preview_configuration()
        preview_config["transform"] = transform
        picam2.configure(preview_config)

        picam2.start()
        self.log.info("Running for 2 seconds in preview move to lock auto exposure")
        time.sleep(2)
        picam2.stop()

        self.log.info("Reconfiguring camera for still")
        # still defaults to full-resolution, auto-exposure and auto-white-balance
        still_config = picam2.create_still_configuration()
        still_config["transform"] = transform
        picam2.configure(still_config)

        picam2.start()
        logging.getLogger('picamera2').setLevel(logging.WARNING)

        image_dir = self.config.image_dir()
        tmp_dir = f"{image_dir}/tmp"
        os.makedirs(tmp_dir, exist_ok=True)
        interval = self.config.interval()
        last_capture_time = 0

        while True:
            usage = self.checkDiskUsage()
            if usage > 0.95:
                self.log.error(f"Refusing to capture image as disk is too full ({usage*100:.1f}%")
                continue
            current_time = time.time()
            slop = 0.01 # seconds
            next_capture_time = max(0, math.floor((current_time + interval - slop) / interval) * interval)
            if last_capture_time:
                desired_capture_time = math.floor((last_capture_time + interval * 1.5) / interval) * interval
            
                if desired_capture_time >= next_capture_time:
                    next_capture_time = desired_capture_time
                else:
                    self.log.warning(f"MISSED {(next_capture_time - desired_capture_time) / interval:.0f} CAPTURES")

            sleep_duration = next_capture_time - current_time

            #time.localtime(next_capture_time).isoformat()
            
            next_capture_time_fmt = (
                datetime.datetime.fromtimestamp(next_capture_time).strftime('%H:%M:%S'))

            #     '%H:%M:%S.'
            #     time.localtime(next_capture_time)
            self.log.info(f"Sleeping {sleep_duration * 1000:.0f}ms until {next_capture_time_fmt}")
            time.sleep(sleep_duration);

            tmp_filename = f"{tmp_dir}/{next_capture_time:.0f}-{os.getpid()}-tmp.jpg"
            dest_filename = f"{image_dir}/{next_capture_time:.0f}.jpg"

            before = time.time()

            picam2.capture_file(tmp_filename)
            if self.test_only:
                os.unlink(tmp_filename)
                sys.exit(0)
            after = time.time()
            os.rename(tmp_filename, dest_filename)
            open(f"{image_dir}/last_capture.timestamp","w").write("\n")
            
            md = picam2.capture_metadata()
            sensor_time_epoch = md['SensorTimestamp']/1e9 - time.clock_gettime(time.CLOCK_BOOTTIME) + time.time()
            sensor_time_fmt = datetime.datetime.fromtimestamp(sensor_time_epoch).strftime('%H:%M:%S.%f')[:-3]
            self.log.info(f"{dest_filename} capture (exp {md['ExposureTime']/1000}ms, sensortime {sensor_time_fmt} took {(after - before) * 1000:.0f}ms")

            self.log.info(f"  metadata: {md}")

        while True:
            startTime = time.time()
            if startTime > (self.last_grab + self.config.interval()):
                usage = self.checkDiskUsage()
                if usage < 0.9 :
                    self.grabMulti()
                    self.last_grab = startTime
                    endTime = time.time()
                    self.log.info("Grab took %.2f seconds", endTime - startTime);
                else:
                    self.log.warning("Disk Usage %d%%, not grabbing new image",
                                     int(usage * 100));
                    time.sleep(60)
            else:
                time.sleep(0.1)

    def run(self):
        self.grabLoop()


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-only", action="store_true", help="Test image capture and exit")
    args = parser.parse_args()

    svc = ImageService(ServiceConfig('./', 'image'), test_only=args.test_only)
    svc.run()
