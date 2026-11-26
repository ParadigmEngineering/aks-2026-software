# Round-trip check: encode a Drive-style URL, then decode it with OpenCV's detector,
# both as a standalone image and pasted onto a fake camera frame (the on-screen overlay).
# Run from this folder: python test_qr_code.py  (no camera or Drive access needed)

import cv2
import numpy as np
from qr_code import make_qr, overlay_qr

url = "https://drive.google.com/file/d/18HEZNRrWU5hk8dvM7vkiR-P_ZMIoAmJg/view?usp=drivesdk"
detector = cv2.QRCodeDetector()

qr = make_qr(url)
assert qr.ndim == 3 and qr.shape[0] == qr.shape[1] >= 300, qr.shape
decoded, _, _ = detector.detectAndDecode(qr)
assert decoded == url, decoded
print("QR round trip OK:", qr.shape)

# Noisy colour frame the size of a 720p anaglyph, QR at half the frame height like photo_capture.py
frame = np.random.default_rng(0).integers(0, 256, (720, 1280, 3), dtype=np.uint8)
small_qr = make_qr(url, 720 // 2)
x, y = overlay_qr(frame, small_qr)
assert (x + small_qr.shape[1], y + small_qr.shape[0]) == (1280 - 10, 720 - 10), (x, y)
decoded, _, _ = detector.detectAndDecode(frame)
assert decoded == url, decoded
print("QR overlay OK at", (x, y))
