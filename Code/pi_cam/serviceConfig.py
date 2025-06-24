import logging
from logging.handlers import TimedRotatingFileHandler
import time
import glob
import os
import os.path
import socket
from sys import exc_info
import configparser
import subprocess

class ServiceConfig:
    '''Wraps common code for reading configuration and logger initialization.'''
    logger: logging.Logger
    parser: configparser.ConfigParser

    def __init__(self, base_dir, logname):
        # Root directory of breathecam working tree (and of the git repo)
        self._base_dir = os.path.realpath(base_dir) + '/'

        self._wait_for_time()
        self._read_config()
        self._log_start(logname)
        self.logger.info('Log started: ID=%s URL=%s', self._camera_id, self._upload_url)

    def _wait_for_time (self):
        # Wait until the system clock is synchronized.  In the current scheme
        # where the timestamp is in the log file name we can't create the log
        # file until we have the time.  Also this insures that none of our
        # services start until we have the time.
        subprocess.run([self._base_dir + "tools/wait_for_ntp.py"])

    def _log_start(self, logname):
        log_file  = os.path.join(self.log_dir(), "breathecam.txt")

        # 2.  Convert the level name ('INFO', etc.) to its int value
        level_name = self.parser['breathecam']['log_level'].upper()
        log_level  = getattr(logging, level_name, logging.INFO)

        # 3.  Daily rotation, keep 14 compressed archives
        handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',          # keyword arg for clarity
            interval=1,
            backupCount=14,
            encoding='utf-8',         # avoids locale-dependent surprises
            delay=True                # don’t open the file until first write
        )
        formatter = logging.Formatter(
            '%(asctime)s %(name)s %(levelname)s: %(message)s')
        handler.setFormatter(formatter)

        # 4.  (Re)initialise the root logger and force any old config out of the way
        logging.basicConfig(level=log_level, handlers=[handler], force=True)

        # 5.  Your module-specific logger
        self.logger = logging.getLogger(logname)

    def _read_config(self):
        self.parser = configparser.ConfigParser()
        self.parser.read(self.config_dir() + "breathecam.ini")
        self._camera_id = self.parser["breathecam"]["camera_id"] or socket.gethostname()
        self._upload_url = self.parser["breathecam"]["upload_url"]
        self._interval = int(self.parser["breathecam"]["interval"])
        self._num_upload_threads = int(self.parser["breathecam"].get("num_upload_threads", "1"))
        self._batch_size = int(self.parser["breathecam"].get("batch_size", "5"))
        self._quality = int(self.parser["breathecam"].get("quality", "90"))
        self._crop_top = int(self.parser["breathecam"].get("crop_top", "0"))
        self._crop_bottom = int(self.parser["breathecam"].get("crop_bottom", "0"))
        self._crop_left = int(self.parser["breathecam"].get("crop_left", "0"))
        self._crop_right = int(self.parser["breathecam"].get("crop_right", "0"))
        self._capture_url = self.parser["breathecam"].get("capture_url", "")
        self._auth_username = self.parser["breathecam"].get("auth_username", "")
        self._auth_password = self.parser["breathecam"].get("auth_password", "")

    def base_dir(self):
        return self._base_dir

    def camera_id(self):
        return self._camera_id

    def upload_url(self):
        return self._upload_url

    def interval(self):
        return self._interval

    def num_upload_threads(self):
        return self._num_upload_threads

    def batch_size(self):
        return self._batch_size

    def quality(self):
        return self._quality

    def crop_top(self):
        return self._crop_top

    def crop_bottom(self):
        return self._crop_bottom

    def crop_left(self):
        return self._crop_left

    def crop_right(self):
        return self._crop_right

    def capture_url(self):
        return self._capture_url

    def auth_username(self):
        return self._auth_username

    def auth_password(self):
        return self._auth_password

    def log_dir(self):
        return self._base_dir + "logs/"

    def image_dir(self) -> str:
        return self._base_dir + "images/"

    def config_dir(self):
        return self._base_dir + "config_files/"


if __name__ == '__main__':
    conf = ServiceConfig('./', 'test')
