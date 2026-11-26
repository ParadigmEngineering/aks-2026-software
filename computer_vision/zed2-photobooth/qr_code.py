"""Turn a URL (e.g. a Google Drive photo link) into a scannable QR code image.

Uses OpenCV's built-in QR encoder, so no extra packages are needed.

Command line:
    python qr_code.py "https://drive.google.com/file/d/<id>/view" -o qr.png
"""

import argparse
from pathlib import Path

import cv2


def make_qr(url, size=400):
    """Return a BGR QR code image of roughly `size` x `size` pixels."""
    # OpenCV returns 1 pixel per module with a white quiet zone already included.
    qr = cv2.QRCodeEncoder.create().encode(url)
    scale = max(1, size // qr.shape[0])
    # INTER_NEAREST keeps the module edges sharp so phones can read it.
    qr = cv2.resize(qr, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    return cv2.cvtColor(qr, cv2.COLOR_GRAY2BGR)


def save_qr(url, path, size=400):
    """Write the QR code for `url` to `path` and return the path."""
    path = Path(path)
    if not cv2.imwrite(str(path), make_qr(url, size)):
        raise OSError(f"Failed to write QR code: {path}")
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("-o", "--out", type=Path, default=Path("qr.png"))
    args = parser.parse_args()
    print(f"QR code saved: {save_qr(args.url, args.out)}")
