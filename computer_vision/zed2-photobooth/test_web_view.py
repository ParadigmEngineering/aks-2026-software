# Self-check for the browser view: page loads, a published frame arrives as a decodable JPEG
# on /stream, and a Take Photo press is reported exactly once.
# Run from this folder: python test_web_view.py  (no camera or Drive access needed)

import urllib.request

import cv2
import numpy as np
from web_view import FrameServer

server = FrameServer(port=0, host="127.0.0.1")  # port 0 = any free port
base = f"http://127.0.0.1:{server.port}"

page = urllib.request.urlopen(base + "/", timeout=5).read()
assert b'src="/stream"' in page and b"/snap" in page
print("Page OK")

frame = np.random.default_rng(0).integers(0, 256, (376, 1344, 3), dtype=np.uint8)
server.show(frame)
with urllib.request.urlopen(base + "/stream", timeout=5) as stream:
    assert stream.readline().strip() == b"--frame"
    assert stream.readline().strip() == b"Content-Type: image/jpeg"
    length = int(stream.readline().split(b":")[1])
    assert stream.readline().strip() == b""
    jpeg = stream.read(length)
decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
assert decoded.shape == frame.shape, decoded.shape
print("Stream OK:", decoded.shape, f"{length // 1024} KB per frame")

assert not server.snap_requested()
urllib.request.urlopen(urllib.request.Request(base + "/snap", method="POST"), timeout=5)
assert server.snap_requested() and not server.snap_requested()
print("Take Photo OK")

server.close()
