import cv2
import math
from ultralytics import YOLO

#Start Webcam
cap = cv2.VideoCapture(0) #0 for webcam, 'filename.mp4' for video, Unsure for zed2 right now
cap.set(3, 640)
cap.set(4,480)

model = YOLO("best.pt")
#Pathway to the yolo model from where this file is in your computer

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
            print("Confidence --->", confidence)
            if confidence <= 0.5: #Only displays a box if white line detection is over a certain confidence level
                continue

            # bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # convert to int values

            # put box in cam
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # class name
            cls = int(box.cls[0])
            print("Class name -->", classNames[cls])

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