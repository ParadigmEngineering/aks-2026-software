import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import serial
import sys

class UartBridge(Node):
    def __init__(self):
        super().__init__('uart_bridge_node')

        # serial port config
        self.serial_port = 'dev/ttsTHS1'
        self.baudrate = 115200

        try:
            self.stm_serial = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            self.get_logger().info(f"SUCCESS: Opened UART on {self.serial_port}")
        except serial.SerialException as e:
            self.get_logger().fatal(f"CRITICAL: Could not open serial port on {self.serial_port}: {e}")
            sys.exit(1)

        self.subscription = self.create_subscription(
            Twist,
            '/cmd_vel',
            self.cmd_vel_callback,
            10
        )

        self.get_logger().info("UART Bridge Online.")
    
    def cmd_vel_callback(self, msg):
        """
        consume throttle and steering data instructions from algo and write to UART bridge comm
        :param msg.x: throttle in RPM (confirm max 4500)
        :param msg.z: steering in PWM or we do the conversion here (confirm 0 to 4000)
        """
        throttle = msg.linear.x
        steering = msg.angular.z

        command_string = f"STR:{steering:.2f},THR:{throttle:.2f}\n"

        try:
            self.stm_serial.write(command_string.encode('utf-8'))
        except serial.SerialException as e:
            self.get_logger().error(f"ERROR: Failed to write to STM: {e}")

def main(args=None):
    rclpy.init(args=args)
    node = UartBridge()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if hasattr(node, 'stm_serial') and node.stm_serial.is_open:
            # graceful shutdown of hardware port
            node.stm_serial.close()
            node.get_logger().info("INFO: serial port closed")
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()