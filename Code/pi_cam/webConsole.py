import flask, json, os, struct, threading, time
import logging
from scrollpos import read_scrollpos, write_scrollpos
from euclid3 import Vector2

os.chdir(os.path.dirname(os.path.realpath(__file__)))

app = flask.Flask(__name__)

# Configure the logger
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s %(name)s %(levelname)s: %(message)s',
                    handlers=[
                        logging.FileHandler("logs/webConsole.log"),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger('webConsole')
@app.get("/")
def index():
    with open("webConsole.html") as file:
        return file.read()

@app.get('/compiled/<path:path>')
def send_compiled(path):
    return flask.send_from_directory('compiled', path)

@app.get("/currentStream")
def current_stream():
    logger.info("Received request for currentStream")

    def stream_jpgs():
        image_path = "images/current/current.jpg"
        last_mtime = 0
        try:
            while True:
                while True:
                    current_mtime = os.path.getmtime(image_path)
                    if current_mtime != last_mtime:
                        break
                    time.sleep(0.05)
                last_mtime = current_mtime

                with open(image_path, "rb") as file:
                    jpeg_data = file.read()
                logger.info(f"Streaming a new frame, size: {len(jpeg_data)} bytes")
                yield struct.pack("<L", len(jpeg_data)) + jpeg_data
        except GeneratorExit:
            logger.warning("Client disconnected, stopping the stream.")
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
    
    return flask.Response(stream_jpgs(), content_type="application/octet-stream")

@app.post("/writeScrollpos")
def write_scrollpos_api():
    write_scrollpos(flask.request.get_json())
    return flask.jsonify(success=True)

# This web API is probably not used because the javascript only writes the scrollpos, 
# but here it is anyway.
@app.get("/readScrollpos")
def read_scrollpos_api():
    sp_vec, mode = read_scrollpos()
    return flask.jsonify({'mode': mode, 'x': sp_vec.x, 'y': sp_vec.y})

if __name__ == "__main__":
    logger.info("Starting Flask server")
    app.run(host="0.0.0.0", port=8000)
