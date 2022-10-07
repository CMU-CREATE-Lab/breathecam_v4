import flask, json, os, struct, threading, time
from scrollpos import read_scrollpos, write_scrollpos

os.chdir(os.path.dirname(os.path.realpath(__file__)))

app = flask.Flask(__name__)

@app.get("/")
def index():
    return open("webConsole.html").read()

@app.get('/compiled/<path:path>')
def send_compiled(path):
    return flask.send_from_directory('compiled', path)

@app.get("/currentStream")
def current_stream():
    def stream_jpgs():
        image_path = "images/current/current.jpg"
        last_mtime = 0
        while True:
            while True:
                current_mtime = os.path.getmtime(image_path)
                if current_mtime != last_mtime:
                    break
                time.sleep(0.05)
            last_mtime = current_mtime

            jpeg_data = open(image_path, "rb").read();
            print(f"yield a frame length {len(jpeg_data)}")
            yield struct.pack("<L", len(jpeg_data)) + jpeg_data
    return stream_jpgs(), {"Content-Type":f"application/octet-stream"}

@app.post("/writeScrollpos")
def write_scrollpos_api():
    write_scrollpos(flask.request.get_json())
    return flask.jsonify(success=True);

@app.get("/readScrollpos")
def read_scrollpos_api():
    return flask.jsonify(read_scrollpos())
