import cv2
import math
import os
import numpy as np
from PIL import ImageGrab
from ultralytics import YOLO

#Kart measurements (in inches)
KART_WIDTH = 52
GROUND_TO_CAMERA = 22
BUMPER_TO_CAMERA = 30

res_x = 1920
res_y = 1080
middle_x = res_x / 4
confidence_threshold = 0.5

#ANSI codes for colouring the powershell output. 
PURPLE = "\033[35m"
PINK = "\033[38;5;212m"
RESET = "\033[0m"

#Checks which camera indexes are available
# for camera_idx in range(10): 
#    cap = cv2.VideoCapture(camera_idx)
#    if cap.isOpened():
#        print(f"Camera index available: {camera_idx}")
#        cap.release() 

#Start Camera
# cap = cv2.VideoCapture(0) #camera index (usually 0 or 1) for webcam/zed 2, 'filename.mp4' for video
# cap.set(3, res_x) #resolution x-value
# cap.set(4, res_y) #resolution y-value
# if not cap.isOpened():
#    print("Couldn't open camera")
#    exit()

#Pathway to the yolo model from where this file is in your computer
model = YOLO("datasets/Grass-Lane_v1/runs/segment/train5/weights/best.pt") 
#C:...\aks-2026-software\computer_vision\datasets\White-Line-Detection_v4\runs\segment\train2\weights

#Object classes
classNames = ["Grass", "Lane"]
class_colour = ""

#Used to determine which class a detection belongs to. True if Lane, False if Grass
def isLane(class_name):
    if classNames[cls].startswith("Lane"):
        return True, PINK
    return False, PURPLE

while True:
    #Camera
    # success, img = cap.read()
    
    #Screen Recording
    cap =  ImageGrab.grab(bbox = (0, 0, int(res_x / 2), res_y))
    img = np.array(cap.getdata(),dtype='uint8').reshape((cap.size[1],cap.size[0],3))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    results, = model(img, stream=True)
    detection_num = 0

    #Coordinates
    for r in results:
        #Why build this loop around bounding boxes when we aren't using them? Because for some reason r.masks doesn't have the
        #confidence score attribute we use to filter out detections
        boxes = r.boxes
        
        for box in boxes:
            #Confidence
            confidence = math.ceil((box.conf[0] * 100)) / 100
            if confidence <= confidence_threshold: #Only displays a detection if it's over a certain confidence level
                continue

            detection_num += 1

            #Class name
            cls = int(box.cls[0])

            #Pixel coordinates
            coords = r.masks.xy

            #Colours in every detected pixel
            if coords is not None:
                for segment in r.masks.xy:
                    polygon = np.array(segment, dtype=np.int32)

                    is_lane, class_colour = isLane(classNames[cls])

                    if is_lane:
                        cv2.fillPoly(img, [polygon], (255,192,203)) 
                    else:
                        cv2.fillPoly(img, [polygon], (128,0,128)) 

            #Terminal output
            print("Class name -->", classNames[cls] + str(detection_num))
            print("Confidence --->", confidence)
            print("Pixel coordinates for " + classNames[cls] + " " + str(detection_num) + ":\n", f"{class_colour}{coords}{RESET}")
            
    cv2.imshow('Webcam', img)

    if cv2.waitKey(1) == ord('q'): #Escape key
        break

# cap.release()
cv2.destroyAllWindows()