#!/usr/bin/env python3
"""
Mock Arduino node to simulate motor control and sensor data
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray
from geometry_msgs.msg import Twist

class MockArduino(Node):
    def __init__(self):
        super().__init__('mock_arduino')
        self.get_logger().info('Mock Arduino Node Started - Simulating Arduino with motors and sensors')
        
        # Publisher for fake sensor data
        self.sensor_publisher = self.create_publisher(Int32MultiArray, 'gas_sensors', 10)
        
        # Subscriber for motor commands
        self.cmd_vel_subscriber = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10)
        
        # Timer for publishing fake sensor data
        self.timer = self.create_timer(0.2, self.publish_sensor_data)
        
        self.get_logger().info('Mock Arduino ready - will simulate motor movement and sensor readings')
        
    def cmd_vel_callback(self, msg):
        """Simulate motor control based on Twist commands"""
        linear_x = msg.linear.x
        angular_z = msg.angular.z
        
        # Convert to motor speeds (simplified)
        left_speed = linear_x - angular_z * 0.5
        right_speed = linear_x + angular_z * 0.5
        
        # Log motor commands
        self.get_logger().info(f'Motors: Left={left_speed:.2f}, Right={right_speed:.2f} | Linear={linear_x:.2f}, Angular={angular_z:.2f}')
        
    def publish_sensor_data(self):
        """Publish fake sensor data"""
        sensor_msg = Int32MultiArray()
        # Simulate normal gas sensor readings
        sensor_msg.data = [300, 250]  # MQ-2, MQ-135 values
        self.sensor_publisher.publish(sensor_msg)

def main(args=None):
    rclpy.init(args=args)
    node = MockArduino()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
