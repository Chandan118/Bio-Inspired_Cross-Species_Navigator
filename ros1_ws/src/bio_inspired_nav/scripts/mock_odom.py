#!/usr/bin/env python3
"""
Mock Odometry Publisher for testing without Gazebo
Simulates robot movement based on cmd_vel commands
"""

import rospy
import math
import numpy as np
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Twist, Quaternion
from sensor_msgs.msg import LaserScan, Imu
from std_msgs.msg import Header


class MockOdometry:
    """Simulates robot odometry without Gazebo"""
    
    def __init__(self):
        rospy.init_node('mock_odom', anonymous=True)
        
        # Robot state
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.vx = 0.0
        self.vtheta = 0.0
        
        # Publishers
        self.odom_pub = rospy.Publisher('/odom', Odometry, queue_size=10)
        self.scan_pub = rospy.Publisher('/scan', LaserScan, queue_size=10)
        self.imu_pub = rospy.Publisher('/imu', Imu, queue_size=10)
        
        # Subscriber
        rospy.Subscriber('/cmd_vel', Twist, self.cmd_vel_callback)
        
        # Timer
        self.last_time = rospy.Time.now()
        self.timer = rospy.Timer(rospy.Duration(0.05), self.update)  # 20 Hz
        
        rospy.loginfo("Mock Odometry Publisher started")
    
    def cmd_vel_callback(self, msg):
        """Receive velocity commands"""
        self.vx = msg.linear.x
        self.vtheta = msg.angular.z
    
    def update(self, event):
        """Update robot state and publish odometry"""
        current_time = rospy.Time.now()
        dt = (current_time - self.last_time).to_sec()
        
        if dt > 0:
            # Update position (simple integration)
            delta_x = self.vx * math.cos(self.theta) * dt
            delta_y = self.vx * math.sin(self.theta) * dt
            delta_theta = self.vtheta * dt
            
            self.x += delta_x
            self.y += delta_y
            self.theta += delta_theta
            self.theta = self.normalize_angle(self.theta)
        
        # Publish odometry
        self.publish_odom(current_time)
        
        # Publish fake LiDAR scan
        self.publish_scan(current_time)
        
        # Publish IMU
        self.publish_imu(current_time)
        
        self.last_time = current_time
    
    def publish_odom(self, current_time):
        """Publish odometry message"""
        odom = Odometry()
        odom.header.stamp = current_time
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_footprint"
        
        # Position
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        
        # Orientation (quaternion from yaw)
        quat = self.euler_to_quaternion(0, 0, self.theta)
        odom.pose.pose.orientation = quat
        
        # Velocity
        odom.twist.twist.linear.x = self.vx
        odom.twist.twist.angular.z = self.vtheta
        
        self.odom_pub.publish(odom)
    
    def publish_scan(self, current_time):
        """Publish fake LiDAR scan"""
        scan = LaserScan()
        scan.header.stamp = current_time
        scan.header.frame_id = "laser"
        
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        scan.angle_increment = math.pi / 180.0  # 1 degree
        scan.time_increment = 0.0
        scan.scan_time = 0.05
        scan.range_min = 0.12
        scan.range_max = 10.0
        
        # Generate fake ranges (random obstacles)
        num_readings = 360
        ranges = []
        for i in range(num_readings):
            # Simulate some obstacles at random positions
            angle = scan.angle_min + i * scan.angle_increment
            
            # Default far range
            r = 10.0
            
            # Add some virtual obstacles
            if abs(angle) < 0.3:  # Front obstacle
                r = 2.0 + np.random.normal(0, 0.1)
            elif abs(angle - math.pi/2) < 0.3:  # Left obstacle
                r = 3.0 + np.random.normal(0, 0.1)
            elif abs(angle + math.pi/2) < 0.3:  # Right obstacle
                r = 3.0 + np.random.normal(0, 0.1)
            
            ranges.append(max(scan.range_min, min(scan.range_max, r)))
        
        scan.ranges = ranges
        self.scan_pub.publish(scan)
    
    def publish_imu(self, current_time):
        """Publish IMU data"""
        imu = Imu()
        imu.header.stamp = current_time
        imu.header.frame_id = "imu_link"
        
        # Orientation
        quat = self.euler_to_quaternion(0, 0, self.theta)
        imu.orientation = quat
        
        # Angular velocity
        imu.angular_velocity.z = self.vtheta
        
        # Linear acceleration (simple model)
        imu.linear_acceleration.x = 0.0
        imu.linear_acceleration.y = 0.0
        imu.linear_acceleration.z = 9.81
        
        self.imu_pub.publish(imu)
    
    def euler_to_quaternion(self, roll, pitch, yaw):
        """Convert Euler angles to quaternion"""
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        
        q = Quaternion()
        q.w = cr * cp * cy + sr * sp * sy
        q.x = sr * cp * cy - cr * sp * sy
        q.y = cr * sp * cy + sr * cp * sy
        q.z = cr * cp * sy - sr * sp * cy
        
        return q
    
    def normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def run(self):
        """Main loop"""
        rospy.spin()


if __name__ == '__main__':
    try:
        mock = MockOdometry()
        mock.run()
    except rospy.ROSInterruptException:
        pass
