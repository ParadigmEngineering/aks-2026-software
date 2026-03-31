import rclpy
import cv2

from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Point ## If this breaks something for you, get rid off all this stuff

class LaneDetector(Node):
    def __init__(self):
        super().__init__('lane_detector')

        self.subscription = self.create_subscription(
            Image,
            'zed/zed_node/rgb/image_rect_color',
            self.image_callback,
            10
        )

        self.lane_center_pub = self.create_publisher(Point, 'lane_center', 10)

        self.test_timer = self.create_timer(1.0, self.publish_test_lane_center)


        self.br = CvBridge()
        self.get_logger().info('Lane Detector node established')
    
    def publish_test_lane_center(self):
        lane_center_msg = Point()
        lane_center_msg.x = 0.0 
        lane_center_msg.y = 0.0 
        lane_center_msg.z = 0.0
        self.lane_center_pub.publish(lane_center_msg)
        self.get_logger().info('Published test lane center')

    def image_callback(self, data):
        current_frame = self.br.imgmsg_to_cv2(data, desired_encoding='bgr8')
        processed_image = self.detect_lanes(current_frame)
        cv2.imshow("Lane Detection Feed", processed_image)
        cv2.waitKey(1)
        
        ## Eventually do something in here maybe
        # lane_center_msg = Point()
        # lane_center_msg.x = 0.0  # Replace with actual lane center x
        # lane_center_msg.y = 0.0  # Replace with actual lane center y
        # lane_center_msg.z = 0.0  # Replace with actual lane center z if needed
        # self.lane_center_pub.publish(lane_center_msg)

    def detect_lanes(self, frame):
        # Example: Convert to grayscale and find edges
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 50, 150)
        return edges

def main(args=None):
    '''
    setup.py looks for a function in this lane_detector so this function call 
    structure is required
    '''
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

    