import json, os, threading
from euclid import Vector2
from typing import Tuple

# Return the scroll position as a Vector2 ranging 0..1 and the string mode
def read_scrollpos() -> Tuple[Vector2, str]:
    try:
        with open("scrollpos.json") as file:
            sp = json.load(file)
        return Vector2(sp['x'], sp['y']), sp['mode']
    except Exception as e:
        print(f"Got exception reading scrollpos.json; returning default ({e})")
        return Vector2(0, 0), "ZoomOut"

def write_scrollpos(sp: dict):
    tmpnam = f"scrollpos-tmp-{os.getpid()}-{threading.get_ident()}.json"
    with open(tmpnam, "w") as file:
        json.dump(sp, file)
    os.rename(tmpnam, "scrollpos.json")
