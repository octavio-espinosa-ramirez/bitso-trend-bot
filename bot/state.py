"""Estado persistente (sobrevive a reinicios). Escritura atómica para no corromper el archivo."""
import json, os, tempfile, threading


class State:
    def __init__(self, path, capital):
        self.path, self.lock = path, threading.RLock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.d = {"cash": capital, "start_capital": capital, "positions": {}, "trades": [],
                  "active": False, "live": False, "day": "", "day_start_equity": capital, "halted": False}
        if os.path.exists(path):
            try:
                self.d.update(json.load(open(path)))
            except Exception:
                os.replace(path, path + ".corrupt")

    def save(self):
        with self.lock:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(self.path)))
            with os.fdopen(fd, "w") as f:
                json.dump(self.d, f, indent=1)
            os.replace(tmp, self.path)
