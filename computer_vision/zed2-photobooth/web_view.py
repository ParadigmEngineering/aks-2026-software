"""Show the photo booth feed in a web browser instead of an OpenCV window.

The Jetson rides on the kart with no screen, so photo_capture.py serves the feed over the
network: open http://<jetson-ip>:8000 on any laptop or phone on the same network.
Frames go out as MJPEG (a stream of JPEGs that browsers play in a plain <img> tag). The
browser scales the image, so a fullscreen view costs no extra bandwidth, unlike X11 forwarding.
A slow viewer just skips frames instead of falling behind, so the feed stays close to live.
"""

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2

PAGE = b"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Paradigm Photo Booth</title>
<style>
  html, body { margin: 0; height: 100%; background: #000; overflow: hidden; }
  img { width: 100vw; height: 100vh; object-fit: contain; display: block; }
  button { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
           font: bold 28px sans-serif; padding: 16px 40px; border: 0; border-radius: 40px;
           background: #fff; opacity: .85; cursor: pointer; }
</style></head><body>
<img src="/stream" alt="Live photo booth camera feed">
<button id="snap">Take photo (P)</button>
<script>
  const snap = () => fetch("/snap", { method: "POST" });
  document.getElementById("snap").onclick = snap;
  document.onkeydown = e => { if (e.key === "p" || e.key === "P") snap(); };
</script></body></html>"""


class FrameServer:
    """Streams the latest frame to every connected browser and records Take Photo presses."""

    def __init__(self, port=8000, host="0.0.0.0", quality=80):
        self.quality = quality
        self._jpeg = None
        self._new_frame = threading.Condition()
        self._snap = threading.Event()
        frames = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(PAGE)))
                    self.end_headers()
                    self.wfile.write(PAGE)
                elif self.path == "/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    frames._stream(self.wfile)
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == "/snap":
                    frames._snap.set()
                    self.send_response(204)
                    self.end_headers()
                else:
                    self.send_error(404)

            def log_message(self, *args):
                pass  # One line per request would flood the terminal

        self._httpd = ThreadingHTTPServer((host, port), Handler)
        self._httpd.daemon_threads = True
        self.port = self._httpd.server_address[1]
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()

    def _stream(self, out):
        sent = None
        try:
            while True:
                with self._new_frame:
                    self._new_frame.wait_for(lambda: self._jpeg is not sent)
                    sent = self._jpeg
                out.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(sent))
                out.write(sent + b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # Browser tab closed

    def show(self, frame):
        """Publish a BGR frame to every connected browser (the cv2.imshow replacement)."""
        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        if ok:
            with self._new_frame:
                self._jpeg = buf.tobytes()
                self._new_frame.notify_all()

    def snap_requested(self):
        """True once per Take Photo press (button or P key in any browser)."""
        if self._snap.is_set():
            self._snap.clear()
            return True
        return False

    def close(self):
        self._httpd.shutdown()
        self._httpd.server_close()
