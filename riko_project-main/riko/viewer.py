"""Her body: a tiny web server for the avatar page (client/index.html).

The page asks /next four times a second. When a new voice clip is waiting,
it plays it, moves her mouth to it, and calls /done when the clip ends, so
push-to-talk only comes back after she has finished talking.

No page open? The clip plays on your speakers instead.
"""
import json
import queue
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import sounddevice as sd
import soundfile as sf

from riko.config import ROOT

HOST, PORT = "127.0.0.1", 8080  # 127.0.0.1, not localhost: behaves the same on Windows and Linux

_clips = queue.Queue()          # voice clips waiting for the page
_finished = threading.Event()   # set when the page says a clip ended
_page_last_seen = float("-inf")  # when the page last asked /next (time.monotonic); never yet
_avatar = None                  # the .vrm file named in character_config.yaml


class _Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        global _page_last_seen
        if self.path == "/avatar.vrm":
            return self._send(_avatar.read_bytes(), "application/octet-stream")
        if self.path != "/next":
            return super().do_GET()  # the page and the voice clip, from client/
        _page_last_seen = time.monotonic()
        try:
            clip = _clips.get_nowait()
        except queue.Empty:
            clip = None
        self._send(json.dumps({"audio": clip}).encode(), "application/json")

    def do_POST(self):
        if self.path == "/done":
            _finished.set()
        self._send(b"{}", "application/json")

    def _send(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # keep the terminal readable


def start(cfg):
    global _avatar
    _avatar = ROOT / cfg["vrm_model"]
    if not _avatar.exists():
        sys.exit(f"[setup] Avatar not found: {_avatar}. Check vrm_model in character_config.yaml.")
    try:
        server = ThreadingHTTPServer((HOST, PORT), partial(_Handler, directory=str(ROOT / "client")))
    except OSError:
        sys.exit(f"[setup] Port {PORT} is busy (is Riko already running?). Close it or change PORT in riko/viewer.py.")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"[viewer] avatar: {cfg['vrm_model']}")
    print(f"[viewer] avatar page: http://{HOST}:{PORT}  (open it, then click once)")


def play(wav_path):
    """Play her voice on the avatar page, or the speakers if no page is open. Returns when she is done."""
    duration = sf.info(wav_path).duration
    if time.monotonic() - _page_last_seen < 2:
        _finished.clear()
        _clips.put(f"audio/{wav_path.name}?v={time.time()}")  # ?v= so the browser never replays the old clip
        if not _finished.wait(timeout=duration + 10):
            print("[viewer] the page never said the clip ended; carrying on")
    else:
        print("[viewer] no avatar page open, playing on speakers")
        data, sample_rate = sf.read(wav_path)
        sd.play(data, sample_rate)
        sd.wait()
