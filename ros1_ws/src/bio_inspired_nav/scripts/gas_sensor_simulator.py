#!/usr/bin/env python3
"""
Gas Sensor Simulator for Gazebo
Simulates gas concentration based on distance from source
"""

import rospy
import math
import numpy as np
from std_msgs.msg import Float32MultiArray
from nav_msgs.msg import Odometry


class GasSensorSimulator:
    """Simulates gas sensor readings based on robot position"""
    
    def __init__(self):
        rospy.init_node('gas_sensor_simulator', anonymous=True)
        
        # Gas source position
        self.source_x = rospy.get_param('~source_x', 8.0)
        self.source_y = rospy.get_param('~source_y', 8.0)
        self.source_strength = rospy.get_param('~source_strength', 1000.0)
        self.decay_rate = rospy.get_param('~decay_rate', 0.5)  # How fast concentration drops with distance
        self.noise_level = rospy.get_param('~noise_level', 50.0)
        self.wind_direction = rospy.get_param('~wind_direction', 0.785)  # radians (45 deg default)
        self.wind_strength = rospy.get_param('~wind_strength', 0.3)
        
        # Robot position
        self.robot_x = 0.0
        self.robot_y = 0.0
        
        # Publishers
        self.gas_pub = rospy.Publisher('/gas_sensors', Float32MultiArray, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        
        # Timer for publishing
        self.timer = rospy.Timer(rospy.Duration(0.1), self.publish_gas_data)
        
        rospy.loginfo("Gas Sensor Simulator initialized")
        rospy.loginfo("Source at ({}, {}) with strength {}".format(
            self.source_x, self.source_y, self.source_strength))
    
    def odom_callback(self, msg):
        """Update robot position"""
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y
    
    def calculate_concentration(self):
        """
        Calculate gas concentration based on Gaussian plume model
        Modified by wind direction and turbulence
        """
        # Distance from source
        dx = self.robot_x - self.source_x
        dy = self.robot_y - self.source_y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance < 0.01:
            return self.source_strength
        
        # Angle from source to robot
        angle_to_robot = math.atan2(dy, dx)
        
        # Wind effect: concentration higher downwind
        angle_diff = self.normalize_angle(angle_to_robot - self.wind_direction)
        wind_factor = 1.0 + self.wind_strength * math.cos(angle_diff)
        
        # Gaussian decay with distance
        concentration = self.source_strength * math.exp(-self.decay_rate * distance) * wind_factor
        
        # Add turbulence (noise)
        noise = np.random.normal(0, self.noise_level)
        concentration = max(0, concentration + noise)
        
        return concentration
    
    def calculate_gradient(self):
        """Calculate concentration gradient (approximation)"""
        current_conc = self.calculate_concentration()
        
        # Small step for finite difference
        step = 0.1
        
        # Sample at nearby points
        original_x = self.robot_x
        original_y = self.robot_y
        
        # Forward
        self.robot_x += step
        conc_forward = self.calculate_concentration()
        self.robot_x = original_x
        
        # Backward
        self.robot_x -= step
        conc_backward = self.calculate_concentration()
        self.robot_x = original_x
        
        # Left
        self.robot_y += step
        conc_left = self.calculate_concentration()
        self.robot_y = original_y
        
        # Right
        self.robot_y -= step
        conc_right = self.calculate_concentration()
        self.robot_y = original_y
        
        # Gradient components
        grad_x = (conc_forward - conc_backward) / (2 * step)
        grad_y = (conc_left - conc_right) / (2 * step)
        
        gradient_magnitude = math.sqrt(grad_x**2 + grad_y**2)
        
        return gradient_magnitude
    
    def normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def publish_gas_data(self, event):
        """Publish simulated gas sensor data"""
        concentration = self.calculate_concentration()
        gradient = self.calculate_gradient()
        
        # Additional simulated sensors
        co2_level = concentration * 0.4 + np.random.normal(0, 10)
        mq135_reading = concentration * 0.6 + np.random.normal(0, 15)
        
        # Distance to source (for evaluation only - real robot wouldn't know this)
        dx = self.robot_x - self.source_x
        dy = self.robot_y - self.source_y
        distance_to_source = math.sqrt(dx**2 + dy**2)
        
        msg = Float32MultiArray()
        msg.data = [
            float(concentration),      # MQ-2 equivalent
            float(gradient),           # Gradient magnitude
            float(co2_level),          # CO2 sensor
            float(mq135_reading),      # MQ-135
            float(distance_to_source)  # Ground truth distance (for metrics)
        ]
        
        self.gas_pub.publish(msg)
    
    def run(self):
        """Main loop"""
        rospy.spin()


if __name__ == '__main__':
    try:
        simulator = GasSensorSimulator()
        simulator.run()
    except rospy.ROSInterruptException:
        pass
