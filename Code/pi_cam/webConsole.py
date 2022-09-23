import os, time
import flask

os.chdir(os.path.dirname(os.path.realpath(__file__)))

app = flask.Flask(__name__)

@app.route("/")
def index():
    return open("webConsole.html").read()

@app.route('/compiled/<path:path>')
def send_compiled(path):
    return flask.send_from_directory('compiled', path)

import struct

@app.route("/current_stream")
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

# @app.route("/current.mjpg")
# def current_mjpg():
#     separator = "frame79p9XvpjB"
#     def stream_mjpg():
#         image_path = "images/current/current.jpg"
#         last_mtime = 0
#         yield f"--{separator}\r\n".encode()
#         while True:
#             while True:
#                 current_mtime = os.path.getmtime(image_path)
#                 if current_mtime != last_mtime:
#                     break
#                 time.sleep(0.05)
#             last_mtime = current_mtime
#             ret = (
#                 b'Content-Type: image/jpeg\r\n\r\n' +
#                 open(image_path, "rb").read() + b'\r\n' +
#                 f"--{separator}\r\n".encode()
#             )
#             # There's a source of latency that causes the frame displayed to be one frame old, at least
#             # when sending from the "flask" development commandline and receiving from Chrome.
#             # Until we're able to track down and fix, send the image twice.
#             yield ret
#             yield ret
#     return stream_mjpg(), {"Content-Type":f"multipart/x-mixed-replace;boundary={separator}"}

