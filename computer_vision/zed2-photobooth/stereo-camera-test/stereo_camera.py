"""Capture raw ZED 2 stereo pairs over USB using OpenCV."""
from __future__ import annotations

import sys
from types import MappingProxyType

import cv2
import numpy as np

__all__ = ["RESOLUTIONS", "capture_stereo"]

# Per-eye width, height, FPS.
RESOLUTIONS = MappingProxyType({
    "720p": (1280, 720, 30),
    "1080p": (1920, 1080, 30),
    "2k": (2208, 1242, 15),
    "vga":(672,376,30)
})


def capture_stereo(
    resolution: str = "720p",
    camera_index: int | None = None,
    *,
    warmup_frames: int = 20,
) -> tuple[np.ndarray, np.ndarray]:
    """Return independent left/right uint8 BGR arrays and release the camera.

    resolution: 720p, 1080p, or 2k (case-insensitive).
    camera_index: OpenCV index; None scans indices 0-5 by frame dimensions.
    warmup_frames: read attempts before returning the last valid frame.
    Raises ValueError for invalid arguments or OSError if capture fails.
    Frames are unrectified; exact dimensions are required. No driver timeout.
    """
    if not isinstance(resolution, str) or resolution.lower() not in RESOLUTIONS:
        raise ValueError("resolution must be '720p', '1080p', or '2k'")
    if camera_index is not None and (
        isinstance(camera_index, bool) or not isinstance(camera_index, int) or camera_index < 0
    ):
        raise ValueError("camera_index must be a non-negative integer or None")
    if isinstance(warmup_frames, bool) or not isinstance(warmup_frames, int) or warmup_frames < 1:
        raise ValueError("warmup_frames must be a positive integer")

    width, height, fps = RESOLUTIONS[resolution.lower()]
    backend = cv2.CAP_DSHOW if sys.platform == "win32" else (
        cv2.CAP_AVFOUNDATION if sys.platform == "darwin" else cv2.CAP_ANY
    )
    indices = range(6) if camera_index is None else (camera_index,)
    errors = []
    for index in indices:
        cap = cv2.VideoCapture(index, backend)
        try:
            if not cap.isOpened():
                errors.append(f"{index}: cannot open device")
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width * 2)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, fps)
            frame = None
            actual_size = None
            for _ in range(warmup_frames):
                ok, image = cap.read()
                if not ok or image is None or image.size == 0:
                    continue
                actual_size = image.shape
                if image.shape == (height, width * 2, 3) and image.dtype == np.uint8:
                    frame = image
            if frame is None:
                errors.append(
                    f"{index}: expected BGR uint8 frame {width * 2}x{height}, "
                    f"received {actual_size or 'no frames'}"
                )
                continue
            # Split a single stereo frame.
            return frame[:, :width].copy(), frame[:, width:].copy()
        except cv2.error as exc:
            errors.append(f"{index}: {exc}")
        finally:
            cap.release()

    raise OSError(
        f"Cannot capture stereo pair {resolution}. "
        "Check USB 3 and camera permissions; close other camera "
        "applications or specify camera_index. "
        + "; ".join(errors)
    )
