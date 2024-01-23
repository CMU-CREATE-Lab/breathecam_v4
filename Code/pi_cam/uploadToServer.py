#!/usr/bin/python3
from collections import defaultdict
import math
import os
import os.path
import time
import requests
import glob

from serviceConfig import ServiceConfig

config = ServiceConfig('./', 'upload')
log = config.logger

BULK_UPLOAD_SIZE = 3

def filenameTimestamp(filename):
    return int(os.path.splitext(os.path.basename(filename))[0])

def uploadFiles(listOfFiles: list[str], thread_id: int) -> int:

    age = round(time.time() - filenameTimestamp(listOfFiles[0]))
    # Format age in human-readable form
    humanReadableAge = f"{age%60}s"
    age //= 60
    if age:
        humanReadableAge = f"{age%60}m" + humanReadableAge
        age //= 60
        if age:
            humanReadableAge = f"{age%24}h" + humanReadableAge
            age //= 24
            if age:
                humanReadableAge = f"{age}d" + humanReadableAge

    log.info(f"th({thread_id}) Uploading age={humanReadableAge} {', '.join([os.path.basename(filename) for filename in listOfFiles])}")

    files = []
    uploadSize = 0
    for filename in listOfFiles:
        # I think we are sending the absolute path to the server,
        # which is kind of random. But this is what the old code did.
        # base = os.path.basename(listOfFiles[x])
        files.append(('images[]', (filename, open(filename, 'rb'), 'image/jpeg')))
        uploadSize += os.path.getsize(filename)
    payload = {'id': config.camera_id(), 'useEXIF': 'false'}
    r = requests.post(config.upload_url(), data=payload, files=files, timeout=60)
    response2 = str(r.json)
    if (response2.find("200") > 0):
        log.info(f"th({thread_id}) Upload of {uploadSize / 1e6:.3f}MB completed in {r.elapsed.total_seconds() * 1000:.0f} ms, {uploadSize * 8 / 1e6 / r.elapsed.total_seconds():.0f} mbit/s")
        for filename in listOfFiles:
            try:
                os.remove(filename)
            except:
                log.warning(f"th({thread_id}) Failed to delete: {filename}")
        return uploadSize
    else:
        failDelay = 5
        log.info(f"th({thread_id}) Upload failed, waiting {failDelay} secs before retry: {response2}")
        # lets not hammer the poor server if it is failing
        time.sleep(failDelay)
        return 0

def uploadForever():
    while True:
        time.sleep(0.25)

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

            if not images:
                continue

            # We must complete upload of a batch before starting the next batch
            batch_size = 60 * config.batch_size()  # Seconds per batch of images
            batches = defaultdict(list)
            for image in images:
                epoch_timestamp = filenameTimestamp(image)
                batchno = epoch_timestamp // batch_size
                batches[batchno].append(image)

            # We're uploading the first batch listed
            batch_to_upload = batches[min(batches.keys())]

            listOfFiles = sorted(batch_to_upload, key=filenameTimestamp)
            listOfFiles = listOfFiles[:BULK_UPLOAD_SIZE * config.num_upload_threads()]
            # Split into max_parallel_uploads batches
            filesPerThread = [listOfFiles[i:i+BULK_UPLOAD_SIZE] for i in range(0, len(listOfFiles), BULK_UPLOAD_SIZE)]

            import concurrent.futures

            beforeUpload = time.monotonic()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for (i, threadFiles) in enumerate(filesPerThread):
                    future = executor.submit(uploadFiles, threadFiles, i)
                    futures.append(future)

                # Wait for all threads to complete
                # Sum all the upload sizes
                uploadSize = sum([future.result() for future in futures])
                uploadTime = time.monotonic() - beforeUpload
                log.info(f"In total, uploaded {uploadSize / 1e6:.3f} MB in {uploadTime*1000:.0f} ms, {uploadSize * 8 / 1e6 / uploadTime:.0f} mbit/s")


        except Exception as e:
            # really any error
            log.error(f"Unexpected error: {repr(e)}")
            time.sleep(5.0)


uploadForever()
