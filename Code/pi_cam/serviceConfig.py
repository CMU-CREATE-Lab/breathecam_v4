import logging
import time
import glob
import os
import os.path
import socket
from sys import exc_info
import configparser

class ServiceConfig:
    '''Wraps common code for reading configuration and logger initialization.'''
    def __init__(self, base_dir, logname):
        # Root directory of breathecam working tree (and of the git repo)
        self._base_dir = os.path.realpath(base_dir) + '/';

        # These are cache variables for the parameters.  This is
        # probably not necessary, people can just use the parser
        # themselves.

        # String name identifying this camera to the upload served
        self._camera_id = ""
        # URL for the upload server
        self._upload_url = ""
        # Float frame interval
        self._interval = ""

        # ConfigParser for breathecam.ini
        self.parser: configparser.ConfigParser = None
        # Logger instance for this service
        self.logger: logging.Logger = None

        self._wait_for_time()
        self._read_config()
        self._log_start(logname)
        self.logger.info('Log started: ID=%s URL=%s', self._camera_id, self._upload_url);

    def _wait_for_time (self):
        # Wait until the system clock is synchronized.  In the current scheme
        # where the timestamp is in the log file name we can't create the log
        # file until we have the time.  Also this insures that none of our
        # services start until we have the time.
        while not os.path.exists("/run/systemd/timesync/synchronized"):
            print("waiting for time sync")
            time.sleep(5.0)

    def _log_start(self, logname):
        # Save old log files and open a new one. We only move files for
        # our 'logname' to avoid a race condition with other processes where
        # we move their newly opened logs.
        #
        # If we used threads then there could be just one logger, which
        # would simplify things.  Even without threads we probably
        # could exploit the append behavior of logging to log all to
        # the same file.
        try:
            os.makedirs(self.log_dir(), exist_ok = True)
            # old_logdir = self.log_dir() + 'old/' 
            # os.makedirs(old_logdir, exist_ok = True)
            # listOfFilesToMove = glob.glob(self.log_dir() + logname + "_*.txt")
            # for fileToMove in listOfFilesToMove:
            #     print("Saving old log "+ fileToMove)
            #     base = os.path.basename(fileToMove)
            #     os.rename(self.log_dir() + base, old_logdir + base)
        except:
            print("Error moving log file" + str(exc_info()[0]))

        # log_file = (self.log_dir() + logname + '_' +
        #            str(int(time.time())) + ".txt")
        log_file = self.log_dir() + "breathecam.txt"
        log_level = logging.getLevelName(self.parser['breathecam']['log_level'])
        logging.basicConfig(level=log_level, filename=log_file,
                            format='%(asctime)s %(name)s %(levelname)s: %(message)s')
        self.logger = logging.getLogger(logname)

    def _read_config(self):
        self.parser = configparser.ConfigParser()
        self.parser.read(self.config_dir() + "breathecam.ini")
        self._camera_id = self.parser["breathecam"]["camera_id"] or socket.gethostname()
        self._upload_url = self.parser["breathecam"]["upload_url"]
        self._interval = float(self.parser["breathecam"]["interval"])

    def base_dir(self):
        return self._base_dir

    def camera_id(self):
        return self._camera_id

    def upload_url(self):
        return self._upload_url

    def interval(self):
        return self._interval

    def log_dir(self):
        return self._base_dir + "logs/"

    def image_dir(self) -> str:
        return self._base_dir + "images/"
        
    def config_dir(self):
        return self._base_dir + "config_files/"


if __name__ == '__main__':
    conf = ServiceConfig('./', 'test');
