import threading
import typing
from typing import Union
import datetime
import math
import sys
from shutil import disk_usage
import time
import logging
from serviceConfig import ServiceConfig
import os
from picamera2 import Picamera2, CompletedRequest
from picamera2.request import _MappedBuffer
import libcamera
import piexif
import json
from PIL import Image
import requests
from requests import Response
from requests.auth import HTTPDigestAuth
from euclid import Vector2
from scrollpos import read_scrollpos

class ImageService:
    def __init__(self, config: ServiceConfig, test_only=False, test_only_save_image=False):
        self.config = config
        self.test_only = test_only
        self.test_only_save_image = test_only_save_image
        self.log = config.logger
        self.last_grab = 0
        bc = config.parser["breathecam"]
        self.rotation = [int(x) for x in bc["rotation"].split()]
        # tuning_file path is relative to the directory of this script
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.tuning_file = os.path.join(script_dir, bc["tuning_file"])
        self.interval = int(bc["interval"]) # in seconds
        self.is_picam = True
        if self.config.capture_url() and self.config.auth_username() and self.config.auth_password():
            self.auth = HTTPDigestAuth(self.config.auth_username(), self.config.auth_password())
            self.is_picam = False


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

        if isinstance(img, bytes):
            with open(file_output, 'wb') as f:
                f.write(img)
        else: # Is an image coming from a picam
            # compress_level=1 saves pngs much faster, and still gets most of the compression.
            png_compress_level = self.picam2.options.get("compress_level", 1)
            jpeg_quality = self.config.quality()
            if format_str in ('jpg', 'jpeg'):
                if img.mode == "RGBA":
                    # Nasty hack. Qt doesn't understand RGBX so we have to use RGBA. But saving a JPEG
                    # doesn't like RGBA to we have to bodge that to RGBX.
                    img.mode = "RGBX"
                # Make up some extra EXIF data.
                zero_ifd = {piexif.ImageIFD.Make: "Raspberry Pi",
                            piexif.ImageIFD.Model: self.picam2.camera.id, # type: ignore
                            piexif.ImageIFD.Software: "Picamera2",
                            piexif.ImageIFD.MakerNoteSafety: 1}
                total_gain = metadata["AnalogueGain"] * metadata["DigitalGain"]
                metadata["JpegQuality"] = jpeg_quality

                exif_ifd = {piexif.ExifIFD.ExposureTime: (metadata["ExposureTime"], 1000000),
                            piexif.ExifIFD.ISOSpeedRatings: int(total_gain * 100),
                            piexif.ExifIFD.MakerNote: f"Picamera2 {json.dumps(metadata)}".encode("utf8")}
                exif = piexif.dump({"0th": zero_ifd, "Exif": exif_ifd})
            img.save(file_output, compress_level=png_compress_level, quality=jpeg_quality, exif=exif)
        end_time = time.monotonic()
        self.log.info(f"Saved image to file {file_output}.")
        self.log.info(f"Time taken for encode: {(end_time-start_time)*1000} ms.")

    def save_file_and_metadata(self, request: Union[CompletedRequest, Response], capture_timestamp: int, rotate_ccw_90: bool):
        image_dir = self.config.image_dir().rstrip("/")
        current_dir = f"{image_dir}/current"
        os.makedirs(current_dir, exist_ok=True)

        if self.is_picam:
            metadata = request.get_metadata() # Copies data from request
            # Create PIL image from request
            img = typing.cast(Image.Image, request.make_image("main")) # Referenced data from request;  do not release request until after done with image
            # Rotate image clockwise 90 degrees using numpy
            if rotate_ccw_90:
                img = img.rotate(90, expand=True)

            if self.config.crop_top() or self.config.crop_bottom() or self.config.crop_left() or self.config.crop_right():
                img = img.crop((
                    self.config.crop_left(), 
                    self.config.crop_top(), 
                    img.width - self.config.crop_right(), 
                    img.height - self.config.crop_bottom()
                    ))
        else:
            metadata = {}
            img = request.content

        # Current image
        current_filename = f"{current_dir}/current.jpg"
        current_tmp_filename = f"{current_dir}/current-tmp{os.getpid()}-{threading.get_ident()}.jpg"
        # File for upload
        upload_filename = f"{image_dir}/{capture_timestamp:.0f}.jpg"

        before = time.monotonic()
        self.save_image(img, metadata, current_tmp_filename, format)

        if self.test_only:
            if self.test_only_save_image:
                os.rename(current_tmp_filename, "/tmp/test.jpg")
                self.log.info("Saved test image to /tmp/test.jpg")
            else:
                os.unlink(current_tmp_filename)
                self.log.info("Deleted test image")
            sys.exit(0)

        # Atomically replace current.jpg, for interactive display (e.g. focusing)
        os.rename(current_tmp_filename, current_filename)

        # Hard-link to image in "to be uploaded" directory
        os.link(current_filename, upload_filename)
        open(f"{image_dir}/last_capture.timestamp","w").write("\n")
        
        extra_logging_info = ""
        if self.is_picam:
            sensor_time_epoch = metadata['SensorTimestamp']/1e9 - time.clock_gettime(time.CLOCK_BOOTTIME) + time.time()
            sensor_time_fmt = datetime.datetime.fromtimestamp(sensor_time_epoch).strftime('%H:%M:%S.%f')[:-3]
            extra_logging_info += f"(exp {metadata['ExposureTime']/1000}ms, sensortime {sensor_time_fmt}"
            # We've copied everything we need from request, so release it for the pipeline to proceed
            request.release()

        after = time.monotonic()
        self.log.info(f"Saving {upload_filename} {extra_logging_info} took {(after - before) * 1000:.0f}ms")
        self.log.debug(f"  metadata: {metadata}")

    # Create a PIL image from the center and corners of the input image img_in. These images are 
    # composited into one image with the sub-images seperated by borders.
    def extractCornersImage(self, img_in):
        # Height, width of the sub-images extracted and composited.
        zoom_window_size = Vector2(320, 240)
        # Width of gray border between the sub images.
        border = 5
        border_color = (128, 128, 128)  # Gray color

        img_width, img_height = img_in.size
        zw_width, zw_height = zoom_window_size.x, zoom_window_size.y

        # Coordinates for the corners and center
        corners = [
            (0, 0),  # top-left
            (img_width - zw_width, 0),  # top-right
            (0, img_height - zw_height),  # bottom-left
            (img_width - zw_width, img_height - zw_height),  # bottom-right
        ]
        center = ((img_width - zw_width) // 2, (img_height - zw_height) // 2)

        # Extract images
        extracted_images = [img_in.crop((x, y, x + zw_width, y + zw_height)) for x, y in corners]
        extracted_images.append(img_in.crop((center[0], center[1], center[0] + zw_width, center[1] + zw_height)))

        # Create the composite image
        composite_width = 3 * zw_width + 4 * border
        composite_height = 3 * zw_height + 4 * border
        composite_image = Image.new('RGB', (composite_width, composite_height), color=border_color)

        # Place the extracted images in the composite image
        positions = [
            (border, border),  # top-left
            (3 * border + 2 * zw_width, border),  # top-right
            (border, 3 * border + 2 * zw_height),  # bottom-left
            (3 * border + 2 * zw_width, 3 * border + 2 * zw_height),  # bottom-right
            (border + zw_width + border, border + zw_height + border)  # center
        ]

        for pos, img in zip(positions, extracted_images):
            composite_image.paste(img, pos)

        return composite_image
    
    # Return a cropped subimage at the position in scrollpos
    def fastZoomImage (self, img_in, scrollpos):
        sensor_res = Vector2(*img_in.size)
        zoom_window_size = Vector2(320, 240)
        desired_center_pixel = Vector2(scrollpos.x * sensor_res.x, scrollpos.y * sensor_res.y)
        desired_upper_left = desired_center_pixel - zoom_window_size / 2
        min_valid = Vector2(0,0)
        max_valid = sensor_res - zoom_window_size
        actual_upper_left = Vector2(
            min(max(desired_upper_left.x, min_valid.x), max_valid.x),
               min(max(desired_upper_left.y, min_valid.y), max_valid.y)
        )
        lower_right = actual_upper_left + zoom_window_size
        sc = [actual_upper_left.x, actual_upper_left.y, lower_right.x, lower_right.y]
        # Extract the rectangle
        return img_in.crop([int(x) for x in sc])
    
    # Check if we are in FastFocus mode.  If so, we take over grabbing as long as we stay in this mode. 
    # Grab is fast as possible, cropped for easier visualization and to reduce the time taken to
    # compress and write the image.
    def fastVideoFocusIfRequested(self):
        scrollpos, z_mode = read_scrollpos();
        if z_mode == "FastFocus":
            self.picam2.stop()
            self.picam2.configure(self.fast_focus_config) # type: ignore
            self.picam2.start()

            # Current image
            current_dir = self.config.image_dir().rstrip("/") + "/current"
            current_filename = f"{current_dir}/current.jpg"
            current_tmp_filename = f"{current_dir}/current-tmp{os.getpid()}-{threading.get_ident()}.jpg"               
            while z_mode == "FastFocus":
                try:
                    request = self.picam2.capture_request()
                    # Create PIL image from request
                    img = request.make_image("main")

                    cropped = self.extractCornersImage(img)
                    # cropped = self.fastZoomImage(img, scrollpos)
                    cropped.save(current_tmp_filename)
                finally:
                    request.release()

                # Sleep sets a max frame rate to keep from swamping the client in worst case
                time.sleep(0.1)
                os.rename(current_tmp_filename, current_filename)
                scrollpos, z_mode = read_scrollpos() # 0-1 in x and y, representing center of zoom

            # Done with fast focus, go back to still_config
            self.picam2.stop()
            self.picam2.configure(self.still_config) # type: ignore
            self.picam2.start()
    
    def grabLoop(self):
        if self.is_picam:
            self.log.info(f"Instantiating Picamera2 with tuning file {self.tuning_file}")
            self.picam2 = Picamera2(tuning=self.tuning_file)
            rotate_ccw = self.rotation[0] % 360
            assert rotate_ccw in (0, 90, 180, 270), "Rotation must be 0, 90, 180, or 270"

            # Round down to nearest 180 for transform since transform can only do 0 or 180
            transform_rotation = rotate_ccw // 180 * 180
            transform = libcamera.Transform(rotation=transform_rotation) # type: ignore
            rotate_ccw_90 = (rotate_ccw - transform_rotation) == 90

            # preview defaults to lower resolution, auto-exposure and auto-white-balance
            preview_config = self.picam2.create_preview_configuration()
            preview_config["transform"] = transform
            self.picam2.configure(preview_config) # type: ignore

            self.picam2.start()
            self.log.info("Running for 2 seconds in preview move to lock auto exposure")
            time.sleep(2)
            self.picam2.stop()

            self.log.info("Reconfiguring camera for still")
            # still defaults to full-resolution, auto-exposure and auto-white-balance
            self.still_config = self.picam2.create_still_configuration(raw={}, buffer_count=1)
            self.still_config["transform"] = transform
            self.log.info(f"Initial config is {self.still_config}")
            self.picam2.align_configuration(self.still_config)
            self.log.info(f"Config after alignment is {self.still_config}")

            # fast focus config
            self.fast_focus_config = self.picam2.create_still_configuration(raw={}, buffer_count=4)
            self.fast_focus_config['transform'] = transform
            self.fast_focus_config['controls']['Sharpness'] = 0
            # BTW noise reduction decreases jpeg size
            self.fast_focus_config['controls']['NoiseReductionMode'] = 0
            self.picam2.align_configuration(self.still_config)
            
            # Select the still config
            self.picam2.configure(self.still_config) # type: ignore
            self.picam2.start()
            logging.getLogger('picamera2').setLevel(logging.WARNING)



        interval = self.config.interval()
        last_capture_time = 0
        all_count = 0
        sentinel_val = b"\xff\x00\x11\xaa\xde\xad\xbe\xef"
        while True:
            # Capture next frame
            before = time.monotonic()
            if self.is_picam:
                self.fastVideoFocusIfRequested()
                request: CompletedRequest = self.picam2.capture_request() # type: ignore
                capture_duration = time.monotonic() - before
                self.log.debug(f"Captured frame in {capture_duration*1000:.1f}ms")
                all_count += 1
                with _MappedBuffer(request, "raw") as b:
                    self.log.debug(f"len={len(b)}, sentinel area={b[-36:-28].hex(' ')}")
                    save_good_bad = False
                    if b[-36:-28] == sentinel_val:
                        self.log.warning("CORRUPT IMAGE!  Skipping.")
                        if save_good_bad:
                            request.save("main", datetime.datetime.now().strftime("test/bad.%H%M%S.%f.jpg"))
                        request.release()
                    else:
                        b[-36:-28] = sentinel_val
                        if save_good_bad:
                            request.save("main", datetime.datetime.now().strftime("test/good.%H%M%S.%f.jpg"))
                        current_time = time.time()
                        # Round down to beginning of current period
                        this_capture_time = math.floor(current_time / interval) * interval
                        if this_capture_time > last_capture_time:
                            last_capture_time = this_capture_time
                            self.save_file_and_metadata(request, this_capture_time, rotate_ccw_90=rotate_ccw_90)
                        else:
                            request.release()
            else:
                current_time = time.time()
                # Round down to beginning of current period
                this_capture_time = math.floor(current_time / interval) * interval
                if this_capture_time > last_capture_time:
                    response = requests.get(self.config.capture_url(), auth=self.auth)
                    capture_duration = time.monotonic() - before
                    self.log.debug(f"Captured frame in {capture_duration*1000:.1f}ms")
                    all_count += 1
                    if response.status_code == 200:
                        last_capture_time = this_capture_time
                        self.save_file_and_metadata(response, this_capture_time, rotate_ccw_90=False)
                    else:
                        self.log.debug(f"Error querying camera. Got a '{response.status_code}' response code.")

    def run(self):
        self.grabLoop()


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-only", action="store_true", help="Test image capture, delete image, and exit")
    parser.add_argument("--test-only-save-image", action="store_true", help="Save image in /tmp during test")
    parser.add_argument("--simulate-camera", action="store_true", help="Simulate camera capture without opening camera")
    args = parser.parse_args()

    svc = ImageService(
        ServiceConfig('./', 'image'),
        test_only=args.test_only,
        test_only_save_image=args.test_only_save_image)
    svc.run()
