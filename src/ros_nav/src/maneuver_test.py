import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import time

class ManeuverTest(Node):
    def __init__(self):
        super().__init__('maneuver_test_node')
        
        # Publish to the topic that our UART bridge is listening to
        self.publisher_ = self.create_publisher(Twist, 'cmd_vel', 10)
        
        # Publish commands at 10Hz
        self.timer = self.create_timer(0.1, self.publish_commands) 
        self.start_time = time.time()
        
        self.get_logger().info("STAND CLEAR: Executing test maneuvers in 3 seconds...")

    def publish_commands(self):
        msg = Twist()
        elapsed = time.time() - self.start_time

        # Note: 1500 is neutral. 
        # (You may need to flip the >1500 / <1500 logic depending on how the STM32 maps it)
        
        if elapsed < 3.0:
            # Stage 0: Safety delay
            msg.linear.x = 1500.0
            msg.angular.z = 1500.0
            self.get_logger().info("WAITING...")
            
        elif elapsed < 6.0:
            # Stage 1: Forward straight
            msg.linear.x = 1530.0 # Slight throttle
            msg.angular.z = 1500.0
            self.get_logger().info("FORWARD")
            
        elif elapsed < 9.0:
            # Stage 2: Steer Left
            msg.linear.x = 1530.0
            msg.angular.z = 1400.0 # Left steering
            self.get_logger().info("LEFT")
            
        elif elapsed < 12.0:
            # Stage 3: Steer Right
            msg.linear.x = 1530.0
            msg.angular.z = 1600.0 # Right steering
            self.get_logger().info("RIGHT")
            
        elif elapsed < 15.0:
            # Stage 4: Straighten out
            msg.linear.x = 1530.0
            msg.angular.z = 1500.0
            self.get_logger().info("STRAIGHT")
            
        else:
            # Stage 5: Stop permanently
            msg.linear.x = 1500.0
            msg.angular.z = 1500.0
            self.get_logger().info("STOP")

        self.publisher_.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = ManeuverTest()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()