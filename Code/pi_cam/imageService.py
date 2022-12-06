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
import piexif
import json

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

    # Code modified from Helpers.save
    def save_image(self, img, metadata, file_output, format=None):
        start_time = time.monotonic()
        exif = b''
        if isinstance(format, str):
            format_str = format.lower()
        elif isinstance(file_output, str):
            format_str = file_output.split('.')[-1].lower()
        else:
            raise RuntimeError("Cannot detemine format to save")
        if format_str in ('jpg', 'jpeg'):
            if img.mode == "RGBA":
                # Nasty hack. Qt doesn't understand RGBX so we have to use RGBA. But saving a JPEG
                # doesn't like RGBA to we have to bodge that to RGBX.
                img.mode = "RGBX"
            # Make up some extra EXIF data.
            zero_ifd = {piexif.ImageIFD.Make: "Raspberry Pi",
                        piexif.ImageIFD.Model: self.picam2.camera.id,
                        piexif.ImageIFD.Software: "Picamera2",
                        piexif.ImageIFD.MakerNoteSafety: 1}
            total_gain = metadata["AnalogueGain"] * metadata["DigitalGain"]
            
            exif_ifd = {piexif.ExifIFD.ExposureTime: (metadata["ExposureTime"], 1000000),
                        piexif.ExifIFD.ISOSpeedRatings: int(total_gain * 100),
                        piexif.ExifIFD.MakerNote: f"Picamera2 {json.dumps(metadata)}".encode("utf8")}
            exif = piexif.dump({"0th": zero_ifd, "Exif": exif_ifd})
        # compress_level=1 saves pngs much faster, and still gets most of the compression.
        png_compress_level = self.picam2.options.get("compress_level", 1)
        jpeg_quality = self.picam2.options.get("quality", 90)
        img.save(file_output, compress_level=png_compress_level, quality=jpeg_quality, exif=exif, format=format)
        end_time = time.monotonic()
        self.log.info(f"Saved {self} to file {file_output}.")
        self.log.info(f"Time taken for encode: {(end_time-start_time)*1000} ms.")

    def capture_file_and_metadata(self, file_output, format=None):
        # Wait for next capture and get its Request, with metadata
        request = self.picam2.capture_request()
        metadata = request.get_metadata() # Copies data from request

        # Create PIL image from request
        img = request.make_image("main") # Copies data from request

        # We've copied everything we need from request, so release it (for the pipeline to proceed?)
        request.release()

        self.save_image(img, metadata, file_output, format)

        return metadata

    def grabLoop(self):
        self.log.info(f"Instantiating Picamera2 with tuning file {self.tuning_file}")
        self.picam2 = Picamera2(tuning=self.tuning_file)
        transform = libcamera.Transform(rotation=self.rotation[0])

        # preview defaults to lower resolution, auto-exposure and auto-white-balance
        preview_config = self.picam2.create_preview_configuration()
        preview_config["transform"] = transform
        self.picam2.configure(preview_config)

        self.picam2.start()
        self.log.info("Running for 2 seconds in preview move to lock auto exposure")
        time.sleep(2)
        self.picam2.stop()

        self.log.info("Reconfiguring camera for still")
        # still defaults to full-resolution, auto-exposure and auto-white-balance
        still_config = self.picam2.create_still_configuration()
        still_config["transform"] = transform
        self.picam2.configure(still_config)

        self.picam2.start()
        logging.getLogger('picamera2').setLevel(logging.WARNING)

        image_dir = self.config.image_dir()
        current_dir = f"{image_dir}/current"
        os.makedirs(current_dir, exist_ok=True)
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

            tmp_filename = f"{current_dir}/{next_capture_time:.0f}-{os.getpid()}-tmp.jpg"
            # Current image
            current_filename = f"{current_dir}/current.jpg"
            # File for upload
            upload_filename = f"{image_dir}/{next_capture_time:.0f}.jpg"

            before = time.time()

            #picam2.capture_file(tmp_filename)
            md = self.capture_file_and_metadata(tmp_filename)
            if self.test_only:
                os.unlink(tmp_filename)
                sys.exit(0)
            after = time.time()
            # Atomically replace current.jpg, for interactive display (e.g. focusing)
            os.rename(tmp_filename, current_filename)
            # Hard-link to image in "to be uploaded" directory
            os.link(current_filename, upload_filename)
            open(f"{image_dir}/last_capture.timestamp","w").write("\n")
            
            sensor_time_epoch = md['SensorTimestamp']/1e9 - time.clock_gettime(time.CLOCK_BOOTTIME) + time.time()
            sensor_time_fmt = datetime.datetime.fromtimestamp(sensor_time_epoch).strftime('%H:%M:%S.%f')[:-3]
            self.log.info(f"{upload_filename} capture (exp {md['ExposureTime']/1000}ms, sensortime {sensor_time_fmt} took {(after - before) * 1000:.0f}ms")

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
