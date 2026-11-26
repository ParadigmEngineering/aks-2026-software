# Paradigm Photo Booth

Extract the ZIP into your project, keep `drive-token.json` beside `photobooth_upload.py`, and install dependencies with `   `. Import `PhotoBoothUploader` with `from paradigm_photo_booth import PhotoBoothUploader` and call `url = PhotoBoothUploader().upload("/path/to/photo.jpg")`. The bundled token lets the module upload to `photo_booth` and return the Google Drive URL without a browser or a fresh sign-in while the token is valid. Keep the ZIP and token private and out of source control. To store the token separately, set `DRIVE_TOKEN_FILE` to its path.
