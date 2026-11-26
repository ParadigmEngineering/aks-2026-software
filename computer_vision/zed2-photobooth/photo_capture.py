# Script which waits until a button is pressed while displaying a live video feed,
# then captures a video frame when a button is pressed and sends it to the 'photos' folder.
# The photo is uploaded to Google Drive in a background thread so the feed keeps moving,
# then a QR code of its Drive link is saved next to the photo (photo_N_qr.png) and shown in
# the corner of the feed for QR_SECONDS, then fades out over FADE_SECONDS.
# Backup: run with --browser-qr to also upload the QR image and open it in a browser tab.

# The anaglyph effect is applied when the video feed is created. It can still work on a one
# lens camera, but the photo will be thinner. To turn off anaglyph change this line:
# photo = make_anaglyph(img) => photo = img

import argparse
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
from anaglyph import make_anaglyph
from photobooth_upload import PhotoBoothUploader
from qr_code import make_qr, overlay_qr, save_qr

QR_SECONDS = 30      # How long the QR code stays on screen after an upload
FADE_SECONDS = 2     # Then it fades out over this long
QR_SCALE = 0.5       # QR code size as a fraction of the feed's shorter side
MESSAGE_SECONDS = 5  # How long the "upload failed" message stays on screen
FONT = cv2.FONT_HERSHEY_SIMPLEX

parser = argparse.ArgumentParser(description="ZED2 photo booth")
parser.add_argument("--browser-qr", action="store_true",
                    help="also upload the QR image to Drive and open it in a browser tab (backup)")
args = parser.parse_args()


def upload(photo_path):
    """Runs in the background thread: upload the photo, save its QR code locally, return its Drive link."""
    uploader = PhotoBoothUploader()
    url = uploader.upload(photo_path)
    print("Photo sent to drive at " + str(url))
    qr_path = save_qr(url, photo_path.with_name(photo_path.stem + "_qr.png"))
    print(f"QR code saved: {qr_path}")
    if args.browser_qr:
        qr_url = uploader.upload(qr_path)
        print("QR code sent to drive at " + str(qr_url))
        webbrowser.open(qr_url)
    return url


def draw_text(frame, text, org):
    """White text with a black outline so it reads on any background."""
    cv2.putText(frame, text, org, FONT, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, text, org, FONT, 0.7, (255, 255, 255), 2, cv2.LINE_AA)


photo_num = 0
destination = Path("photos") # Set this string to where your 'photos' folder is
destination.mkdir(parents = True, exist_ok = True) # Creates a photos folder if none is in the current directory

# Checks which camera indexes are available
for camera_idx in range(6):
   cap = cv2.VideoCapture(camera_idx)
   if cap.isOpened():
       print(f"Camera index available: {camera_idx}")
       cap.release()

# Open the camera
cap = cv2.VideoCapture(0)

if not cap.isOpened():
   print("Couldn't open camera")
   exit()

print("Press P to take a photo")

uploader_thread = ThreadPoolExecutor(max_workers=1)
pending = None       # Upload in progress (a Future), None when idle
qr = None            # QR code image currently on screen
qr_until = 0
message = ""
message_until = 0

try:
    while True:
        # Read frames from the camera
        success, img = cap.read()
        if not success:
            print("Failed to capture")
            break

        photo = make_anaglyph(img)
        frame = photo.copy()  # Overlay is drawn on this copy only, never on the saved photo

        # Pick up a finished upload and turn its link into a QR code
        if pending is not None and pending.done():
            try:
                url = pending.result()
                qr = make_qr(url, int(min(frame.shape[:2]) * QR_SCALE))
                qr_until = time.monotonic() + QR_SECONDS + FADE_SECONDS
            except Exception as e:
                print(f"Failed to upload photo to drive: {e}")
                message, message_until = "Upload failed, try again", time.monotonic() + MESSAGE_SECONDS
            pending = None

        # Draw the overlay
        now = time.monotonic()
        if pending is not None:
            draw_text(frame, "Uploading...", (10, 30))
        elif now < message_until:
            draw_text(frame, message, (10, 30))
        elif qr is not None and now < qr_until:
            with_qr = frame.copy()
            x, y = overlay_qr(with_qr, qr)
            label = "Scan for your photo"
            (text_w, _), _ = cv2.getTextSize(label, FONT, 0.7, 4)
            draw_text(with_qr, label, (min(x, frame.shape[1] - text_w - 10), y - 10))
            # Fully visible for QR_SECONDS, then blends back into the feed over FADE_SECONDS
            fade = min(1.0, (qr_until - now) / FADE_SECONDS)
            frame = cv2.addWeighted(with_qr, fade, frame, 1 - fade, 0)

        # Display the camera feed
        cv2.imshow("Camera", frame)

        # Waits for a button input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('p') or key == ord('P'): # Photo taken
            if pending is not None:
                print("Still uploading the last photo, wait for its QR code")
                continue
            qr = None  # Hide the last guest's QR code

            # Create a name and destination for the photo
            photo_num += 1
            filename = f"photo_{photo_num}.png"
            photo_path = destination / filename

            # Makes sure photos don't get overwritten when the script is ran multiple times
            while photo_path.exists():
                photo_num += 1
                filename = f"photo_{photo_num}.png"
                photo_path = destination / filename

            # Saves the photo to the 'photos' folder, then uploads it in the background
            if cv2.imwrite(str(photo_path), photo):
                print(f"Photo saved: {photo_path}")
                pending = uploader_thread.submit(upload, photo_path)
            else:
                print("Failed to save photo")

finally:
    cap.release()
    cv2.destroyAllWindows()
    uploader_thread.shutdown(wait=True)  # Let an upload in progress finish before exiting

# Press ctrl + c in the terminal to terminate the script
