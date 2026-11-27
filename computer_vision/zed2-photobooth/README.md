# Paradigm Photo Booth

Extract the ZIP into your project, keep `drive-token.json` beside `photobooth_upload.py`, and install dependencies with `pip install opencv-python google-api-python-client google-auth-oauthlib`. Import `PhotoBoothUploader` with `from photobooth_upload import PhotoBoothUploader` and call `url = PhotoBoothUploader().upload("/path/to/photo.jpg")`. The bundled token lets the module upload to `photo_booth` and return the Google Drive URL without a browser or a fresh sign-in while the token is valid. Keep the ZIP and token private and out of source control. To store the token separately, set `DRIVE_TOKEN_FILE` to its path.

## QR code

After each photo, `photo_capture.py` uploads it to `photo_booth` in a background thread (the live feed keeps running and shows "Uploading..."), then saves a QR code of the photo's Drive link next to it as `photos/photo_N_qr.png` and shows it in the bottom-right corner of the feed for 30 seconds (`QR_SECONDS`), then fades it out over 2 seconds (`FADE_SECONDS`). The QR is drawn on the screen only, never on the saved photo. Pressing `P` while an upload is running is ignored; the next photo hides the previous QR. Every upload is shared as "anyone with the link can view".

Backup: `python photo_capture.py --browser-qr` also uploads the QR image to `photo_booth` and opens it in a browser tab.
- Run from this folder: `python photo_capture.py`, open the browser view (below), press `P` to take a photo. Ctrl+C in the terminal to stop.
- QR for any link by hand: `python qr_code.py "<url>" -o qr.png`
- Self-check (no camera or Drive needed): `python test_qr_code.py`
