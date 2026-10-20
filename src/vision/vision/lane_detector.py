import rclpy
import cv2

from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Quaternion ## If this breaks something for you, get rid off all this stuff``

from ultralytics import YOLO
import torch

class LaneDetector(Node):
    def __init__(self):
        super().__init__('lane_detector')

        


        path_to_model = '/home/paradigm/Code/GitHub/aks-2026-software/computer_vision/datasets/White-Line-Detection_v6/runs/segment/train2/weights/best.pt' # TODO: reevaluate
        path_to_engine = '/home/paradigm/Code/GitHub/aks-2026-software/computer_vision/datasets/White-Line-Detection_v6/runs/segment/train2/weights/best.pt' # TODO: reevaluate

        self.TRACK_WIDTH = 163 # Changed
        self.middle_track_width = self.TRACK_WIDTH / 2.0

        self.bridge = CvBridge()
        self.latest_depth_map = None
        
        # load AI model
        self.model = YOLO(path_to_engine, task='segment')

        cuda_status = torch.cuda.is_available()
        self.get_logger().info(f"CUDA STATUS: = {cuda_status}")
        if cuda_status:
            self.get_logger().info("GUCCI")
            self.get_logger().info(f"PyTorch CUDA: {torch.cuda.get_device_name(0)}")
            self.get_logger().info(f"V: {torch.version.cuda}")
        self.get_logger().info(f"YOLO D: {self.model.device}")

        self.image_subscription = self.create_subscription(
            Image,
            'zed/zed_node/rgb/color/rect/image', # TODO: test this with an unrectified image feed
            self.image_callback,
            10
        )

        self.depth_subscription = self.create_subscription(
            Image,
            '/zed/zed_node/depth/depth_registered',
            self.depth_callback,
            10
        )

        self.lane_center_pub = self.create_publisher(Point, 'lane_center', 1)

        #self.test_timer = self.create_timer(1.0, self.publish_test_lane_center)
        
        self.get_logger().info('Lane Detector node established')
    
    def publish_test_lane_center(self):
        lane_center_msg = Point()
        lane_center_msg.w = 0.0
        lane_center_msg.x = 0.0 
        lane_center_msg.y = 0.0 
        lane_center_msg.z = 0.0
        self.lane_center_pub.publish(lane_center_msg)
        self.get_logger().info('Published test lane center')

    def image_callback(self, data):
        """
        
        :param data: tbd
        """
        # TODO: uncomment these lines once depth is fully integrated
        # if self.latest_depth_map is None:
            # return

        current_frame = self.bridge.imgmsg_to_cv2(data, desired_encoding='bgr8')
        lane_data = self.detect_lanes(current_frame)
        msg = Point()

        if lane_data is not None:
            turn_detected, cross_track_error, confidence_score = lane_data

            # TODO: reassess data type -- keeping it in point format using x and y only
            msg.w = float(turn_detected)
            msg.x = float(cross_track_error)
            msg.y = float(confidence_score)
            msg.z = 0.0
            
        else:
            msg.w = 0.0 # no turn detected
            msg.x = 0.0
            msg.y = 0.0
            msg.z = -1.0 # use as error flag -- throw out
        
        self.lane_center_pub.publish(msg)
    
    def depth_callback(self, data):
        """
        cache depth map as raw float array in meters
        :param data: tbd
        """
        self.latest_depth_map = self.bridge.imgmsg_to_cv2(data, desired_encoding='passthrough')
        

    def detect_lanes(self, frame):
        """
        run inference on provided frame and detect white lines of track lane edge
        :param frame: 
        :return lane_data: tuple (bottom_left_x, bottom_right_x, lateral_offset_ratio, confidence_score)
        """
        results = self.model(frame, stream=False, verbose=False)

        height, width, _ = frame.shape
        middle_x = width / 2.0

        valid_lines = []

        for r in results:
            if r.masks is None or r.boxes is None:
                continue
            
            for i, mask in enumerate(r.masks.xy):
                confidence_score = float(r.boxes.conf[i])

                # don't process trash / empties
                if confidence_score < 0.5 or len(mask) == 0:
                    continue

                #mask.sort(key = lambda y: y[mask[1]]) # Sort list by y-value ascending 
                mask = mask[mask[:, 1].argsort()]

                mid = len(mask) // 2
                topHalf = mask[:mid]
                bottomHalf = mask[mid:]
                
                avg_x_bottomHalf = sum(pt[0] for pt in bottomHalf) / len(bottomHalf)
                avg_x_topHalf = sum(pt[0] for pt in topHalf) / len(topHalf)
                avg_x = sum(pt[0] for pt in mask) / len(mask)
                avg_y = sum(pt[1] for pt in mask) / len(mask)

                bottom_point = max(mask, key=lambda pt: pt[1])
                bottom_x = bottom_point[0]

                valid_lines.append({
                    "avg_x": avg_x,
                    "avg_x_bottomHalf": avg_x_bottomHalf,
                    "avg_x_topHalf": avg_x_topHalf,
                    "avg_y": avg_y,
                    "bottom_x": bottom_x,
                    "confidence_score": confidence_score
                })

        if len(valid_lines) < 2:
            return None

        # if len(valid_lines) == 0:
        #     return None
        
        # sorts the list from lowest avg_x (leftmost) to highest avg_x (rightmost)
        # valid_lines.sort(key=lambda line: line["avg_x"])

        # if len(valid_lines) < 2:
        #     if valid_lines[0]["x_coordAvg"] < middle_x:
        #         left_line = valid_lines[0]
        #         bottom_left_x = leftLine["bottom_x"]
        #         bottom_right_x = width
        #     else:
        #         right_line = valid_lines[0]
        #         bottom_right_x = rightLine["bottom_x"]
        #         bottom_left_x = 0
        # else:
        # left_line = valid_lines[0]
        # right_line = valid_lines[-1]

        # bottom_left_x = left_line["bottom_x"]
        # bottom_right_x = right_line["bottom_x"]

        # --- NEW LOGIC: Match the Vision Dev's Line Selection ---
        left_candidates = []
        right_candidates = []

        # 1. Split lines into left and right of the screen
        for line in valid_lines:
            if line["avg_x"] < middle_x:
                left_candidates.append(line)
            else:
                right_candidates.append(line)

        # 2. Safety check: We need at least one line on each side
        if not left_candidates or not right_candidates:
            return None 

        # 3. Pick the line closest to the camera (highest avg_y) for each side
        left_line = max(left_candidates, key=lambda line: line["avg_y"])
        right_line = max(right_candidates, key=lambda line: line["avg_y"])
        # --------------------------------------------------------

        bottom_left_x = left_line["bottom_x"]
        bottom_right_x = right_line["bottom_x"]
        
        # average confidence scores
        confidence_score = (left_line["confidence_score"]+right_line["confidence_score"]) / 2.0

        # compute Cross-Track Error (CTE)
        # lateral_offset_ratio = (min(abs((bottom_right_x - middle_x)), abs((middle_x - bottom_left_x))) - (middle_x))/(middle_x)

        # if abs((bottom_right_x - middle_x)) < abs((middle_x - bottom_left_x)):         
        #     lateralOffsetRatio = lateralOffsetRatio * -1.0

        # middleTrackWidth = TRACK_WIDTH / 2
        # cross_track_error = middleTrackWidth * lateralOffsetRatio

        #------New CTE calculations-----------
        lane_middle = (bottom_left_x + bottom_right_x) / 2.0
        lateral_offset_ratio = (lane_middle - middle_x) / middle_x

        lane_width_pixels = bottom_right_x - bottom_left_x
        pixel_offset = lane_middle - middle_x
        cross_track_error = ((pixel_offset / lane_width_pixels) * self.TRACK_WIDTH)
        #-------------------------------------

        #--------Turn Detection-------------
        turn_detected = 0.0
        
        # right turn incoming
        if (left_line["avg_x_topHalf"] - left_line["avg_x_bottomHalf"]) > 200: #This int will decide how soon you want to start slowing down
            turn_detected = -1.0
        # left turn incoming
        elif (right_line["avg_x_bottomHalf"] - right_line["avg_x_topHalf"]) > 200: #This int will decide how soon you want to start slowing down
            turn_detected = 1.0

        # package results and return
        lane_data = (turn_detected, cross_track_error, confidence_score)
        return lane_data
        #---------------------------------

def main(args=None):
    """
    setup.py looks for a function in this lane_detector so this function call 
    structure is required
    """
    rclpy.init(args=args)
    node = LaneDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()
    
if __name__ == '__main__':
    main()

    