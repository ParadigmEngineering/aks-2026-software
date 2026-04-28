import cv2
import math
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

    rightLine = []
    rightLineAvg = 0

    leftLine = []
    leftLineAvg = 0

    box1_xSum = 0
    box2_xSum = 0

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

            if whiteLine_num == 1: #Set the first detection as the left line 
                leftLine = coords
                leftLineAvg = x_coordAvg

            elif whiteLine_num >= 2:
                if leftLineAvg >= x_coordAvg: #If the current left line average is to the right of x_coordAvg
                    rightLineAvg = leftLineAvg
                    rightLine = leftLine
                    leftLineAvg = x_coordAvg
                    leftLine = coords
                else: #If the current left line average is to the left of x_coordAvg
                    rightLineAvg = x_coordAvg
                    rightLine = coords

            # print("Average x coordinate of White Line " + str(whiteLine_num) + ": " + str(x_coordAvg))

            #Crunch coordinates 
            # centerList = []
            # xList = []
            # savedX = 0
            # horizontalLineCheck = 0
            # for o in coords:
            #     xList = []
            #     savedX = 0
            #     for i in o:
            #         if i[1] >= int(res_y / 2) or i[1] <= int(res_y * 0.66): #first value for center and second value for 2 thirds up.
            #             if i[0] not in xList:
            #                 xList.append(i[0])
            #                 if i[0] == savedX:
            #                     print("Already Saved")
            #                     horizontalLineCheck += 1
            #                     if horizontalLineCheck > 5 and i[1] == 400:
            #                         print("Sharp Turn Approaching")
            #                         horizontalLineCheck = 0
            #                     elif horizontalLineCheck != 5:
            #                         print("No curve yet")
                            
            #                 elif i[0] > savedX * 1.05:
            #                     #Gap detected
            #                     print("gap")
            #                     center = savedX + (i[0]-savedX)/2
            #                     centerXY = [center,i[1]]
            #                     if centerXY not in centerList:
            #                         centerList.append(centerXY) 
            #                         savedX = i[0]
            #                         horizontalLineCheck = 0
            #                     else:
            #                         savedX = i[0]
            #                         horizontalLineCheck = 0

            #                 else:
            #                     print("Same line")
            #             else:
            #                 print("Unkown Error")
            # print(centerList)

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

    print("Left Line Coordinates:")
    print(leftLine)
    print("Right Line Coordinates")
    print(rightLine)
    
    #Find the bottom left and right whiteline pixel coordinates, then calculate the lateral offset ratio using those coords plus the middle x coord of the image
    minLeftY = 0
    bottomLeft_x = 0
    minRightY = 0
    bottomRight_x = 0
    
    for coord in leftLine:
        for element in coord:
            if element[1] > minLeftY:
                minLeftY = element[1]
                bottomLeft_x = element[0]
    for coord in rightLine:
        for element in coord:
            if element[1] > minRightY:
                minRightY = element[1]
                bottomRight_x = element[0]

    print("bottomLeft_x: " + str(bottomLeft_x))
    print("bottomRight_x: " + str(bottomRight_x))

    lateralOffsetRatio = 0
    lateralOffsetRatio = (min(abs((bottomRight_x - middle_x)), abs((middle_x - bottomLeft_x))) - (middle_x)) / (middle_x)
    print("Lateral Offset Ratio: " + str(lateralOffsetRatio))
            
    cv2.imshow('Webcam', img)

    if cv2.waitKey(1) == ord('q'): #Escape key
        break

#cap.release()
cv2.destroyAllWindows()