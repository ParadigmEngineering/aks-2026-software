import rclpy
from rclpy.qos import qos_profile_sensor_data
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
import math
import os

class CircuitSeeker(Node):
    def __init__(self):
        super().__init__('circuit_seek_node')

        # 1. Load the Waypoints from your generated text files
        self.lats = []
        self.lons = []
        self.load_waypoints()
        
        # 2. Waypoint Tracking Variables
        self.wp_index = 0  # Start at Point 1 (Index 0)
        self.arrival_radius = 1  # Meters. How close the kart needs to get before targeting the next point

        # State Variables
        self.current_lat = None
        self.current_lon = None
        self.current_heading = None

        # PID Tuning (Proportional Gain)
        self.Kp_steer = 5.0 

        # Publishers & Subscribers
        self.cmd_pub = self.create_publisher(Twist, 'cmd_vel', 10)
        self.gps_sub = self.create_subscription(NavSatFix, '/mavros/global_position/global', self.gps_cb, qos_profile_sensor_data)
        self.compass_sub = self.create_subscription(Float64, '/mavros/global_position/compass_hdg', self.compass_cb, qos_profile_sensor_data)

        # Control Loop running at 10Hz
        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info(f"Circuit Loaded: {len(self.lats)} Waypoints. Waiting for GPS...")

    def load_waypoints(self):
        # Dynamically find your data folder and read the text files
        base_path = os.path.expanduser('~/Code/GitHub/aks-2026-software/src/ros_nav/data/2025-2026/mun_run')
        
        try:
            with open(os.path.join(base_path, 'latitudes.txt'), 'r') as f:
                self.lats = [float(line.strip()) for line in f if line.strip()]
            with open(os.path.join(base_path, 'longitudes.txt'), 'r') as f:
                self.lons = [float(line.strip()) for line in f if line.strip()]
                
            if len(self.lats) != len(self.lons) or len(self.lats) == 0:
                self.get_logger().fatal("Mismatch or empty waypoint files!")
                raise Exception("Invalid waypoint data")
                
        except Exception as e:
            self.get_logger().fatal(f"Failed to load waypoints: {e}")
            raise

    def gps_cb(self, msg):
        if not math.isnan(msg.latitude):
            self.current_lat = msg.latitude
            self.current_lon = msg.longitude

    def compass_cb(self, msg):
        self.current_heading = msg.data

    def calculate_bearing_and_distance(self, target_lat, target_lon):
        lat1, lon1 = math.radians(self.current_lat), math.radians(self.current_lon)
        lat2, lon2 = math.radians(target_lat), math.radians(target_lon)
        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = 6371000 * c 

        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        bearing_rad = math.atan2(y, x)
        bearing_deg = (math.degrees(bearing_rad) + 360) % 360

        return bearing_deg, distance

    def control_loop(self):
        if self.current_lat is None or self.current_heading is None:
            return

        # Fetch the current target waypoint coordinates
        target_lat = self.lats[self.wp_index]
        target_lon = self.lons[self.wp_index]

        target_bearing, distance_to_target = self.calculate_bearing_and_distance(target_lat, target_lon)

        # Check if we have arrived at the waypoint
        if distance_to_target < self.arrival_radius:
            self.get_logger().info(f"✅ Reached Waypoint {self.wp_index + 1}! Switching to next...")
            
            # This modulo math loops 14 back to 0!
            self.wp_index = (self.wp_index + 1) % len(self.lats) 
            return # Exit loop early so next cycle calculates new bearing

        # --- THE P-CONTROLLER ---
        heading_error = target_bearing - self.current_heading

        if heading_error > 180:
            heading_error -= 360
        elif heading_error < -180:
            heading_error += 360

        steering_pwm = 1500 + (heading_error * self.Kp_steer)
        steering_pwm = max(1100, min(1900, steering_pwm))

        msg = Twist()
        msg.linear.x = 1530.0 # Throttle: Slow forward
        msg.angular.z = float(steering_pwm)
        self.cmd_pub.publish(msg)

        self.get_logger().info(f"WP: {self.wp_index + 1}/{len(self.lats)} | Dist: {distance_to_target:.1f}m | Err: {heading_error:.0f} | Steer PWM: {steering_pwm:.0f}")

def main(args=None):
    rclpy.init(args=args)
    node = CircuitSeeker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
