import supervision as sv
import numpy as np
from ultralytics import YOLO

VIDEO_PATH = "purdueTestClip.mp4"

model = YOLO("best.pt")

video_info = sv.VideoInfo.from_video_path(VIDEO_PATH)

box_annotator = sv.BoxAnnotator(thickness=4, text_thickness=4, text_scale=2)

def process_frame(frame: np.ndarray, _) -> np.ndarray:
    results = model(frame, imgsz=1280)[0]

    detections = sv.Detections.from_yolov8(results)

    labels = [f"{model.names[class_id]} {confidence:0.2f}" for _, _, confidence, class_id, _ in detections]
    frame = box_annotator.annotate(scene=frame, detections=detections, labels=labels)

    return frame

i = 0

while i < 60:
    sv.process_video(source_path=VIDEO_PATH, target_path=f"result.mp4", callback=process_frame)
    i+=1
    