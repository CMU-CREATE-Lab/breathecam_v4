import flask, json, os, struct, threading, time

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
def write_scrollpos():
    pos = flask.request.get_json()
    tmpnam = f"scrollpos-tmp-{os.getpid()}-{threading.get_ident()}.json"
    json.dump(pos, open(tmpnam, "w"))
    os.rename(tmpnam, "scrollpos.json")
    return flask.jsonify(success=True);

@app.get("/readScrollpos")
def read_scrollpos():
    try:
        sp = json.load(open("scrollpos.json"))
        pos = dict(x=sp['x'], y=sp['y'])
    except Exception as e:
        print(f"Got exception reading scrollpos.json; returning default ({e})")
        pos = dict(x=0, y=0)
    return flask.jsonify(pos)
