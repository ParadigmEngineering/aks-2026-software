import cv2
import math
import numpy as np
from PIL import ImageGrab
from ultralytics import YOLO

# Kart measurements (in inches)
KART_WIDTH = 52
GROUND_TO_CAMERA = 22
BUMPER_TO_CAMERA = 30
TRACK_WIDTH = 163
MIDDLE_TRACK_WIDTH = TRACK_WIDTH / 2
# Zed 2 res: 1280, 720, pixel size 2um x 2um
# zed 2 lens size: 2mm

res_x = 1920
res_y = 1080
middle_x = res_x / 2
#warning_threshold = 0.8
confidence_threshold = 0.5

#Checks which camera indexes are available
# for camera_idx in range(10): 
#    cap = cv2.VideoCapture(camera_idx)
#    if cap.isOpened():
#        print(f"Camera index available: {camera_idx}")
#        cap.release() 

#Start Camera
# cap = cv2.VideoCapture(0) # Camera index (usually 0 or 1) for webcam/zed 2, 'filename.mp4' for video
# cap.set(3, res_x) # Resolution x-value
# cap.set(4, res_y) # Resolution y-value

if not cap.isOpened():
   print("Couldn't open camera")
   exit()

# Pathway to the yolo model from where this file is in your computer
model = YOLO("datasets/White-Line-Detection_v6/runs/segment/train2/weights/best.pt") 
# C:...\aks-2026-software\computer_vision\datasets\White-Line-Detection_v4\runs\segment\train2\weights

# Object classes
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

    # Coordinates
    for r in results:
        boxes = r.boxes
        
        for box in boxes:
            # Confidence
            confidence = math.ceil((box.conf[0] * 100)) / 100
            if confidence <= confidence_threshold: # Only displays a box if white line detection is over a certain confidence level
                continue
            print("Confidence --->", confidence)

            whiteLine_num += 1

            # Bounding box
            x1, y1, x2, y2 = box.xyxy[0]
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # Convert to int values
                
            # Put box in cam
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 3)

            # Class name
            cls = int(box.cls[0])
            print("Class name -->", classNames[cls] + str(whiteLine_num))

            # Pixel coordinates of white line objects
            coords = r.masks.xy
            # print("Pixel coordinates: White Line " + str(whiteLine_num))
            # print(coords)

            x_coordSum = 0
            y_coordSum = 0
            x_coordAvg = 0
            y_coordAvg = 0
            count = 0

            # coords.sort(key = lambda y: y[pt[1]]) # Sort list by y-value ascending 

            # mid = len(mask) // 2
            # bottomHalf = mask[:mid]
            # topHalf = mask[mid:]
            
            # avg_x_bottomHalf = sum(pt[0] for pt in bottomHalf) / len(bottomHalf)
            # avg_x_topHalf = sum(pt[0] for pt in topHalf) / len(topHalf)
            # avg_x = (avg_x_bottomHalf + avg_x_topHalf) / 2
            # avg_y = sum(pt[1] for pt in mask) / len(mask)

            for coordinate in coords:
                for element in coordinate:
                    x_coordSum += element[0]
                    y_coordSum += element[1]
                    count += 1
            x_coordAvg = x_coordSum / count
            y_coordAvg = y_coordSum / count

            all_points = [pt for segment in coords for pt in segment]

            bottom_point = max(all_points, key=lambda pt: pt[1]) # Take the bottom-most (aka biggest y-value) point
            bottom_x = bottom_point[0] # Then store the its x value
            bottom_x_str = "Bottom x: " + str(bottom_point[0]) + ", " + str(bottom_point[1]) 

            valid_lines.append({
                "x_coordAvg": x_coordAvg,
                "y_coordAvg": y_coordAvg,
                "bottom_x": bottom_x,
                "bottom_x_str": bottom_x_str
            })

            # Object details
            org = [x1, y1]
            font = cv2.FONT_HERSHEY_SIMPLEX
            fontScale = 1
            color = (255, 0, 0)
            thickness = 2

            # Colours in every detected pixel
            if r.masks is not None:
                for segment in r.masks.xy:
                    polygon = np.array(segment, dtype=np.int32)
                    cv2.fillPoly(img, [polygon], (0,255,0)) 

            cv2.putText(img, classNames[cls] + str(whiteLine_num), org, font, fontScale, color, thickness)

    valid_lines.sort(key = lambda line: line["x_coordAvg"]) # Sort the valid detected lines by leftmost x_coordAvg to rightmost

    if len(valid_lines) < 2:
        cv2.imshow('Webcam', img)

        if cv2.waitKey(1) == ord('q'):
            break

    # Of the detected valid lines, get the bottom x point of the leftmost and rightmost lines
    # elif len(valid_lines) < 2:
    #     if valid_lines[0]["x_coordAvg"] < middle_x:
    #         leftLine = valid_lines[0]
    #         bottomLeft_x = leftLine["bottom_x"]
    #         bottomRight_x = res_x # If no rightLine, assume everything right of leftLine is track
    #     else:
    #         rightLine = valid_lines[0]
    #         bottomRight_x = rightLine["bottom_x"]
    #         bottomLeft_x = 0 # If no leftLine, assume everything left of rightLine is track
            
    # else:
    #     leftLine = valid_lines[0]
    #     bottomLeft_x = leftLine["bottom_x"]
    #     rightLine = valid_lines[-1]
    #     bottomRight_x = rightLine["bottom_x"]
    
    left_candidates = []
    right_candidates = []

    # 1. Split lines into left and right of the screen
    for line in valid_lines:
        if line["x_coordAvg"] < middle_x:
            left_candidates.append(line)
        else:
            right_candidates.append(line)

    # 2. Safety check: We need at least one line on each side
    if left_candidates and right_candidates:

        # 3. Pick the line closest to the camera (highest avg_y) for each side
        left_line = max(left_candidates, key=lambda line: line["y_coordAvg"])
        right_line = max(right_candidates, key=lambda line: line["y_coordAvg"])

        bottom_left_x = left_line["bottom_x"]
        bottom_right_x = right_line["bottom_x"]

        # Print statements for debugging
        if "left_line" in locals():
            print("Left Line:")
            print("x_coordAvg:", left_line["x_coordAvg"])
            print(left_line["bottom_x_str"])

        if "right_line" in locals():
            print("Right Line:")
            print("x_coordAvg:", right_line["x_coordAvg"])
            print(right_line["bottom_x_str"])

        # lane_center = (bottom_left_x + bottom_right_x) / 2.0
        # lateral_offset_ratio = (lane_center - middle_x) / middle_x
        # cross_track_error = MIDDLE_TRACK_WIDTH * lateral_offset_ratio

        lane_center = (bottom_left_x + bottom_right_x) / 2.0
        lateral_offset_ratio = (lane_center - middle_x) / middle_x
        
        lane_width_pixels = bottom_right_x - bottom_left_x
        pixel_offset = lane_center - middle_x
        cross_track_error = ((pixel_offset / lane_width_pixels) * TRACK_WIDTH)
        
        # lateral_offset_ratio = (min(abs((bottom_right_x - middle_x)), abs((middle_x - bottom_left_x))) - (middle_x)) / (middle_x)
        # if abs((bottom_right_x - middle_x)) < abs((middle_x - bottom_left_x)):
        #     lateral_offset_ratio = lateral_offset_ratio * -1.0
        # print("Lateral Offset Ratio: " + str(lateral_offset_ratio))

        # cross_track_error = MIDDLE_TRACK_WIDTH * lateral_offset_ratio
        # print("Cross Track Error: " + str(cross_track_error))

        #-----------Turn Detection--------------------
        # # left turn incoming
        # if (left_line["avg_x_bottomHalf"] - left_line["avg_x_topHalf"]) > 100 #This int will decide how soon you want to start slowing down
        #     # update a message
        #     pass
        # # right turn incoming
        # else if (right_line["avg_x_topHalf"] - right_line["avg_x_bottomHalf"]) > 100 #This int will decide how soon you want to start slowing down)
        #     # update a message
        #     pass

        print("lane_center: " + str(lane_center))
        print("Lateral Offset Ratio: " + str(lateral_offset_ratio))
        print("Cross Track Error: " + str(cross_track_error))

    cv2.imshow('Webcam', img) # Display frame

    if cv2.waitKey(1) == ord('q'): # Escape key
        break

#cap.release()
cv2.destroyAllWindows()