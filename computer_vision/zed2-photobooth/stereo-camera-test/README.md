Connect the ZED 2 via USB 3, enable camera access, close other camera applications, install `opencv-python numpy` with pip, and place `stereo_camera.py` beside your script.
Use `from stereo_camera import capture_stereo` and `left, right = capture_stereo("1080p", camera_index=0)` to get raw BGR NumPy arrays; omit `camera_index` to scan indices 0–5.
Modes (per eye): `"720p"` = 1280×720 at 30 FPS, `"1080p"` = 1920×1080 at 30 FPS, `"2k"` = 2208×1242 at 15 FPS.
