import cv2
import math
import numpy as np
from PIL import ImageGrab
from ultralytics import YOLO

res_x = 1920
res_y = 1080

#Checks which camera indexes are available
#for camera_idx in range(10): 
#    cap = cv2.VideoCapture(camera_idx)
#    if cap.isOpened():
#        print(f"Camera index available: {camera_idx}")
#        cap.release() 

#Start Webcam
# cap = cv2.VideoCapture(1) #camera index (usually 0 or 1) for webcam/zed 2, 'filename.mp4' for video
# cap.set(3, res_x) #resolution x-value
# cap.set(4, res_y) #resolution y-value

# if not cap.isOpened():
#    print("Couldn't open camera")
#    exit()

#Pathway to the yolo model from where this file is in your computer
model = YOLO("datasets/White-Line-Detection_v4/runs/segment/train2/weights/best.pt") 
#C:...\aks-2026-software\computer_vision\datasets\White-Line-Detection_v4\runs\segment\train2\weights

#Object classes
classNames = ["white line"]

while True:
    #Camera
    # success, img = cap.read()
    
    #Screen Recording
    cap =  ImageGrab.grab(bbox = (0, 0, int(res_x / 2), res_y))
    img = np.array(cap.getdata(),dtype='uint8').reshape((cap.size[1],cap.size[0],3))
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    results, = model(img, stream=True)
    whiteLine_num = 0

    # coordinates
    for r in results:
        boxes = r.boxes

        for box in boxes:
            # confidence
            confidence = math.ceil((box.conf[0] * 100)) / 100
            if confidence <= 0.5: #Only displays a box if white line detection is over a certain confidence level
                continue
            print("Confidence --->", confidence)

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
            whiteLine_num += 1
            print("Pixel coordinates: White Line " + str(whiteLine_num))
            print(coords)

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

            # finds the top-left and bottom-right pixel
            #points = coords[0]

            #x_start = int(points[:,0].min())
            #y_start = int(points[:,1].min())
            #x_end   = int(points[:,0].max())
            #y_end   = int(points[:,1].max())

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

    cv2.imshow('Webcam', img)

    if cv2.waitKey(1) == ord('q'): #Escape key
        break

#cap.release()
cv2.destroyAllWindows()