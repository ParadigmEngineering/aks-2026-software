# Round-trip check: encode a Drive-style URL, then decode it with OpenCV's detector.
# Run from this folder: python test_qr_code.py  (no camera or Drive access needed)

import cv2
from qr_code import make_qr

url = "https://drive.google.com/file/d/18HEZNRrWU5hk8dvM7vkiR-P_ZMIoAmJg/view?usp=drivesdk"
qr = make_qr(url)

assert qr.ndim == 3 and qr.shape[0] == qr.shape[1] >= 300, qr.shape
decoded, _, _ = cv2.QRCodeDetector().detectAndDecode(qr)
assert decoded == url, decoded
print("QR round trip OK:", qr.shape)
