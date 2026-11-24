# Script which waits until a button is pressed while displaying a live video feed, 
# then captures an video frame when a buton is pressed and sends it to the 'photos' folder.

# The anaglyph effect is applied when the video feed is created. It can still work on a one
# lens camera, but the photo will be thinner. To turn off anaglyph change these lines:
# cv2.imshow("Camera", make_anaglyph(img)) => cv2.imshow("Camera", img)
# if cv2.imwrite(str(photo_path), make_anaglyph(img)): => if cv2.imwrite(str(photo_path), img):

import cv2
from pathlib import Path
from anaglyph import make_anaglyph

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
cap = cv2.VideoCapture(1)

if not cap.isOpened():
   print("Couldn't open camera")
   exit()

print("Press P to take a photo")

try:
    while True:
        # Read frames from the camera
        success, img = cap.read()
        if not success:
            print("Failed to capture")
            break

        # Display the camera feed
        cv2.imshow("Camera", make_anaglyph(img))

        # Waits for a button input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('p') or key == ord('P'): # Photo taken     
            # Create a name and destination for the photo   
            photo_num += 1
            filename = f"photo_{photo_num}.png"
            photo_path = destination / filename

            # Makes sure photos don't get overwritten when the script is ran multiple times
            while photo_path.exists():
                photo_num += 1
                filename = f"photo_{photo_num}.png"
                photo_path = destination / filename

            # Saves the photo to the 'photos' folder
            if cv2.imwrite(str(photo_path), make_anaglyph(img)):
                print(f"Photo saved: {photo_path}")
            else:
                print("Failed to save photo")

finally:
    cap.release()
    cv2.destroyAllWindows()

# Press ctrl + c in the terminal to terminate the script
    