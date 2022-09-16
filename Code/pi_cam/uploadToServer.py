#!/usr/bin/python3
import os
import os.path
import time
import requests
import glob
import sys
import logging

from serviceConfig import ServiceConfig

config = ServiceConfig('./', 'upload')
log = config.logger

BULK_UPLOAD_SIZE = 3

while True:
    time.sleep(0.1)

    try:
        # We sort by modification time and don't send the most recent file, to
        # avoid race condition where the image is currently being captured and
        # only partly written.
        #
        #### It's conceivable that if there are a stupidly large number of
        #### files waiting to be sent that it could take longer to do this
        #### list-and-sort than it takes to capture an image, in which case we
        #### could never catch up.  Could change the loop to send the oldest
        #### first, and only look for new images when the oldest are used up.
        images = glob.glob(config.image_dir()+"*.jpg")
        l = [(os.stat(i).st_mtime, i) for i in images]
        l.sort()
        listOfFiles = [i[1] for i in l]
        # Truncate at BULK_UPLOAD_SIZE
        listOfFiles = listOfFiles[:BULK_UPLOAD_SIZE]
        files = []

        if listOfFiles:
            log.info(f"Sending {listOfFiles}")
            for filename in listOfFiles:
                # I think we are sending the absolute path to the server,
                # which is kind of random. But this is what the old code did.
                # base = os.path.basename(listOfFiles[x])
                files.append(('images[]', (filename, open(filename, 'rb'), 'image/jpeg')))
            payload = {'id': config.camera_id(), 'useEXIF': 'false'}
            r = requests.post(config.upload_url(), data=payload, files=files, timeout=60)
            response2 = str(r.json)
            if (response2.find("200") > 0):
                log.debug("Got a 200 from server, image upload successful")
                for filename in listOfFiles:
                    try:
                        os.remove(filename)
                    except:
                        log.warning(f"Failed to delete: {filename}")
            else:
                log.error("Upload failed: " + response2)
                # lets not hammer the poor server if it is failing
                time.sleep(5)
        else:
            log.debug("No images to upload...")
            time.sleep(5)

    except Exception as e:
        # really any error
        log.error(f"Unexpected error: {repr(e)}")
        time.sleep(5.0)
