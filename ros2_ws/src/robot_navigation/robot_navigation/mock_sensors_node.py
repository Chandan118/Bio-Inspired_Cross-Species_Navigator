#!/usr/bin/env python3
"""
Mock sensors node to provide fake LiDAR and IMU data for testing
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan, Imu
from geometry_msgs.msg import Quaternion
import math
import time

class MockSensors(Node):
    def __init__(self):
        super().__init__('mock_sensors')
        self.get_logger().info('Mock Sensors Node Started')
        
        # Publisher for fake LiDAR data
        self.lidar_publisher = self.create_publisher(LaserScan, 'scan', 10)
        
        # Publisher for fake IMU data
        self.imu_publisher = self.create_publisher(Imu, 'imu/data', 10)
        
        # Timer for publishing fake data
        self.timer = self.create_timer(0.1, self.publish_sensor_data)
        
        self.angle_offset = 0.0
        
    def publish_sensor_data(self):
        # Create fake LiDAR scan data
        scan_msg = LaserScan()
        scan_msg.header.stamp = self.get_clock().now().to_msg()
        scan_msg.header.frame_id = 'laser_frame'
        scan_msg.angle_min = -math.pi
        scan_msg.angle_max = math.pi
        scan_msg.angle_increment = math.pi / 180.0  # 1 degree
        scan_msg.time_increment = 0.0
        scan_msg.scan_time = 0.1
        scan_msg.range_min = 0.1
        scan_msg.range_max = 10.0
        
        # Generate fake range data - clear path ahead
        num_ranges = int((scan_msg.angle_max - scan_msg.angle_min) / scan_msg.angle_increment)
        scan_msg.ranges = []
        
        for i in range(num_ranges):
            angle = scan_msg.angle_min + i * scan_msg.angle_increment
            
            # Create a clear path ahead (no obstacles)
            if abs(angle) < math.pi/6:  # Front 60 degrees
                scan_msg.ranges.append(5.0)  # Clear path 5 meters ahead
            else:
                scan_msg.ranges.append(3.0)  # Side obstacles at 3 meters
        
        # Publish LiDAR data
        self.lidar_publisher.publish(scan_msg)
        
        # Create fake IMU data
        imu_msg = Imu()
        imu_msg.header.stamp = self.get_clock().now().to_msg()
        imu_msg.header.frame_id = 'imu_frame'
        
        # Set orientation (no rotation)
        imu_msg.orientation.w = 1.0
        imu_msg.orientation.x = 0.0
        imu_msg.orientation.y = 0.0
        imu_msg.orientation.z = 0.0
        
        # Set angular velocity (no rotation)
        imu_msg.angular_velocity.x = 0.0
        imu_msg.angular_velocity.y = 0.0
        imu_msg.angular_velocity.z = 0.0
        
        # Set linear acceleration (no acceleration)
        imu_msg.linear_acceleration.x = 0.0
        imu_msg.linear_acceleration.y = 0.0
        imu_msg.linear_acceleration.z = 9.81  # Gravity
        
        # Publish IMU data
        self.imu_publisher.publish(imu_msg)
        
        # Increment angle for slight movement
        self.angle_offset += 0.01

def main(args=None):
    rclpy.init(args=args)
    node = MockSensors()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
