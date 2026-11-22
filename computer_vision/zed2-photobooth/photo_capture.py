# Script which waits until a button is pressed, then captures an image
# then send it to the 'photos' folder. Next step is making it compatible 
# with ZED 2, adding an anaglyph effect, and putting the Paradigm logo
# in the corner

import cv2
from pathlib import Path

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

try:
    while True:
        # Read frames from the camera
        success, img = cap.read()
        if not success:
            print("Failed to capture")
            break

        # Display the camera feed
        cv2.imshow("Camera", img)

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
            if cv2.imwrite(str(photo_path), img):
                print(f"Photo saved: {photo_path}")
            else:
                print("Failed to save photo")

finally:
    cap.release()
    cv2.destroyAllWindows()

    