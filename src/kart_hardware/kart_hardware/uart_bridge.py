import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial
import sys

FLAG_AUTONOMOUS_ENABLE = 1 << 0  # 0x01
FLAG_ESTOP_REQUEST     = 1 << 1  # 0x02
FLAG_VALID_PATH        = 1 << 2  # 0x04

class UartBridge(Node):
    def __init__(self):
        super().__init__('uart_bridge_node')

        # Updated to the port that worked in your test script
        self.serial_port = '/dev/ttyUSB0' 
        self.baudrate = 115200
        self.sequence = 0

        # Default safe RC PWM values (1500 = neutral)
        self.current_throttle = 1500
        self.current_steering = 1500

        # 1. Initialize Serial
        try:
            self.stm_serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            self.get_logger().info(f"SUCCESS: Opened UART on {self.serial_port}")
        except serial.SerialException as e:
            self.get_logger().fatal(f"CRITICAL: Could not open serial port {self.serial_port}")
            sys.exit(1)

        # 2. Subscribe to the Twist commands
        self.subscription = self.create_subscription(
            Twist,
            'cmd_vel',
            self.twist_callback,
            10
        )

        # 3. Create a 50Hz heartbeat timer (0.02 seconds)
        self.timer = self.create_timer(0.02, self.transmit_packet)
        self.get_logger().info("UART Bridge initialized. Transmitting at 50Hz.")

    def twist_callback(self, msg):
        # Update the stored commands whenever a new ROS message arrives
        self.current_throttle = int(msg.linear.x)
        self.current_steering = int(msg.angular.z)

    def checksum_xor(self, data):
        chk = 0
        for b in data:
            chk ^= b
        return chk

    def transmit_packet(self):
        # Tell the STM32 we are alive and the path is valid
        flags = FLAG_AUTONOMOUS_ENABLE | FLAG_VALID_PATH 

        packet = bytearray([
            0xAA,
            0x55,
            0x01,
            0x06,
            self.sequence & 0xFF,
        ])

        # Little-endian bit shifting for 16-bit integers
        packet.append(self.current_throttle & 0xFF)
        packet.append((self.current_throttle >> 8) & 0xFF)

        packet.append(self.current_steering & 0xFF)
        packet.append((self.current_steering >> 8) & 0xFF)

        packet.append(flags & 0xFF)
        packet.append(self.checksum_xor(packet))

        try:
            self.stm_serial.write(packet)
            self.sequence = (self.sequence + 1) & 0xFF
        except Exception as e:
            self.get_logger().error(f"Failed to write to serial: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = UartBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()