"""Combine side-by-side OpenCV frames using Stereo3D's red-cyan channel mix."""


def make_anaglyph(stereo_frame):
    """Return a BGR image with red from the left and green/blue from the right."""
    midpoint = stereo_frame.shape[1] // 2
    result = stereo_frame[:, midpoint:].copy()
    result[:, :, 2] = stereo_frame[:, :midpoint, 2]
    return result
