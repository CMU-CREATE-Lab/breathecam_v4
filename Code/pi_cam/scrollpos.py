import json, os, threading
from euclid import *

def read_scrollpos() -> Vector2:
    try:
        sp = json.load(open("scrollpos.json"))
        return Vector2(sp['x'], sp['y'])
    except Exception as e:
        print(f"Got exception reading scrollpos.json; returning default ({e})")
        return Vector2(0, 0)

def write_scrollpos(pos: Vector2):
    tmpnam = f"scrollpos-tmp-{os.getpid()}-{threading.get_ident()}.json"
    json.dump(dict(x=pos.x, y=pos.y), open(tmpnam, "w"))
    os.rename(tmpnam, "scrollpos.json")
