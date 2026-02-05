import cv2
import math
from ultralytics import YOLO

#Checks which camera indexes are available
#for camera_idx in range(10): 
#    cap = cv2.VideoCapture(camera_idx)
#    if cap.isOpened():
#        print(f"Camera index available: {camera_idx}")
#        cap.release() 

#Start Webcam
cap = cv2.VideoCapture(0) #camera index (usually 0 or 1) for webcam/zed 2, 'filename.mp4' for video
cap.set(3, 640)
cap.set(4,480)

#Pathway to the yolo model from where this file is in your computer
model = YOLO("datasets/White-Line-Detection_v4/runs/segment/train2/weights/best.pt") 
#C:...\aks-2026-software\computer_vision\datasets\White-Line-Detection_v4\runs\segment\train2\weights

#Object classes
classNames = ["white line"]

if not cap.isOpened():
    print("Couldn't open camera")
    exit()

while True:
    success, img = cap.read()
    results, = model(img, stream=True)

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
            print("Class name -->", classNames[cls])

            # pixel coordinates of white line objects
            coords = r.masks.xy
            print("Pixel coordinates -->", coords)

            # object details
            org = [x1, y1]
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            color = (255, 0, 0)
            thickness = 2

            cv2.putText(img, classNames[cls], org, font, fontScale, color, thickness)

    cv2.imshow('Webcam', img)

    if cv2.waitKey(1) == ord('q'): #Escape key
        break

cap.release()
cv2.destroyAllWindows()