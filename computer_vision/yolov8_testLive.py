import cv2
import math
import numpy as np
from PIL import ImageGrab
from ultralytics import YOLO

#Kart measurements (in inches)
KART_WIDTH = 52
GROUND_TO_CAMERA = 22
BUMPER_TO_CAMERA = 30
TRACK_WIDTH = 177.165
# Zed 2 res: 1280, 720, pixel size 2um x 2um
# zed 2 lens size: 2mm

res_x = 1920
res_y = 1080
middle_x = res_x / 4
warning_threshold = 0.8
confidence_threshold = 0.5

#Checks which camera indexes are available
for camera_idx in range(10): 
   cap = cv2.VideoCapture(camera_idx)
   if cap.isOpened():
       print(f"Camera index available: {camera_idx}")
       cap.release() 

#Start Camera
cap = cv2.VideoCapture(0) #camera index (usually 0 or 1) for webcam/zed 2, 'filename.mp4' for video
cap.set(3, res_x) #resolution x-value
cap.set(4, res_y) #resolution y-value

if not cap.isOpened():
   print("Couldn't open camera")
   exit()

#Pathway to the yolo model from where this file is in your computer
model = YOLO("datasets/White-Line-Detection_v4/runs/segment/train2/weights/best.pt") 
#C:...\aks-2026-software\computer_vision\datasets\White-Line-Detection_v4\runs\segment\train2\weights

#Object classes
classNames = ["white line"]

while True:
    #Camera
    success, img = cap.read()
    
    #Screen Recording
    # cap =  ImageGrab.grab(bbox = (0, 0, int(res_x / 2), res_y))
    # img = np.array(cap.getdata(),dtype='uint8').reshape((cap.size[1],cap.size[0],3))
    # img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    results, = model(img, stream=True)
    whiteLine_num = 0

    valid_lines = []

    # coordinates
    for r in results:
        boxes = r.boxes
        
        for box in boxes:
            # confidence
            confidence = math.ceil((box.conf[0] * 100)) / 100
            if confidence <= confidence_threshold: #Only displays a box if white line detection is over a certain confidence level
                continue
            print("Confidence --->", confidence)

            whiteLine_num += 1

            # bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # convert to int values
                
            # put box in cam
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # class name
            cls = int(box.cls[0])
            print("Class name -->", classNames[cls] + str(whiteLine_num))

            # pixel coordinates of white line objects
            coords = r.masks.xy
            # print("Pixel coordinates: White Line " + str(whiteLine_num))
            # print(coords)

            x_coordSum = 0
            x_coordAvg = 0
            count = 0

            for coordinate in coords:
                for element in coordinate:
                    x_coordSum += element[0]
                    count += 1
            x_coordAvg = x_coordSum / count

            all_points = [pt for segment in coords for pt in segment]
            bottom_point = max(all_points, key=lambda pt: pt[1])
            bottom_x = bottom_point[0]
            bottom_x_str = "Bottom x: " + str(bottom_point[0]) + ", " + str(bottom_point[1])

            valid_lines.append({
                "x_coordAvg": x_coordAvg,
                "bottom_x": bottom_x,
                "bottom_x_str": bottom_x_str
            })

            # object details
            org = [x1, y1]
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            color = (255, 0, 0)
            thickness = 2

            # colours in every detected pixel
            if r.masks is not None:
                for segment in r.masks.xy:
                    polygon = np.array(segment, dtype=np.int32)
                    cv2.fillPoly(img, [polygon], (0,255,0)) 

            #cv2.line(img, (x_start, y_start), (x_end, y_end), (0, 255, 0), 3) # Draws a line between the top-left and bottom-right pixels
            cv2.putText(img, classNames[cls] + str(whiteLine_num), org, font, fontScale, color, thickness)

    if len(valid_lines) == 0:
        continue

    valid_lines.sort(key = lambda line: line["x_coordAvg"])

    if len(valid_lines) < 2:
        if valid_lines[0]["x_coordAvg"] < middle_x:
            leftLine = valid_lines[0]
            bottomLeft_x = leftLine["bottom_x"]
        else:
            rightLine = valid_lines[0]
            bottomRight_x = rightLine["bottom_x"]
    else:
        leftLine = valid_lines[0]
        bottomLeft_x = leftLine["bottom_x"]
        rightLine = valid_lines[-1]
        bottomRight_x = rightLine["bottom_x"]

    if "leftLine" in locals():
        print("Left Line:")
        print("x_coordAvg:", leftLine["x_coordAvg"])
        print(leftLine["bottom_x_str"])

    if "rightLine" in locals():
        print("Right Line:")
        print("x_coordAvg:", rightLine["x_coordAvg"])
        print(rightLine["bottom_x_str"])

    lateralOffsetRatio = 0
    lateralOffsetRatio = (min(abs((bottomRight_x - middle_x)), abs((middle_x - bottomLeft_x))) - (middle_x)) / (middle_x)
    if abs((bottomRight_x - middle_x)) < abs((middle_x - bottomLeft_x)):
        lateralOffsetRatio = lateralOffsetRatio * -1.0
    print("Lateral Offset Ratio: " + str(lateralOffsetRatio))

    middleTrackWidth = TRACK_WIDTH / 2
    crossTrackError = middleTrackWidth * lateralOffsetRatio
    print("Cross Track Error: " + str(crossTrackError))
            
    cv2.imshow('Webcam', img)

    if cv2.waitKey(1) == ord('q'): #Escape key
        break

#cap.release()
cv2.destroyAllWindows()