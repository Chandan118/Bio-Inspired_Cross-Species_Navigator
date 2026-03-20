#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gas Plume Tracking with Gradient-Based Learning
Implements bio-inspired chemotaxis algorithms
"""

import rospy
import numpy as np
import math
from collections import deque
from std_msgs.msg import Float32MultiArray
from geometry_msgs.msg import Twist, Point
from nav_msgs.msg import Odometry


class GasPlumeTracker:
    """
    Bio-inspired gas plume tracking using gradient-based learning
    Mimics moth and insect chemotaxis behavior
    """
    
    def __init__(self):
        rospy.init_node('gas_plume_tracker', anonymous=True)
        
        # Parameters
        self.learning_rate = rospy.get_param('~learning_rate', 0.1)
        self.gradient_window = rospy.get_param('~gradient_window', 10)
        self.surge_speed = rospy.get_param('~surge_speed', 0.3)
        self.cast_angular_vel = rospy.get_param('~cast_angular_vel', 0.8)
        self.plume_threshold = rospy.get_param('~plume_threshold', 100.0)
        self.timeout = rospy.get_param('~timeout', 5.0)
        
        # State machine states
        self.state = 'SEARCHING'  # SEARCHING, TRACKING, CASTING, SURGE
        
        # Sensor history
        self.concentration_history = deque(maxlen=self.gradient_window)
        self.position_history = deque(maxlen=self.gradient_window)
        self.time_history = deque(maxlen=self.gradient_window)
        
        # Current sensor readings
        self.current_concentration = 0.0
        self.current_position = [0.0, 0.0]
        self.current_yaw = 0.0
        self.last_sensor_time = None
        
        # Gradient estimation
        self.gradient_vector = np.array([0.0, 0.0])
        self.gradient_magnitude = 0.0
        self.gradient_direction = 0.0
        
        # Learned parameters (adaptive)
        self.optimal_surge_duration = 2.0  # seconds
        self.optimal_cast_duration = 1.5  # seconds
        self.cast_direction = 1.0  # 1 for left, -1 for right
        
        # Performance tracking
        self.success_count = 0
        self.failure_count = 0
        self.peak_concentration = 0.0
        self.source_estimate = [0.0, 0.0]
        
        # Publishers
        self.cmd_vel_pub = rospy.Publisher('/gas_plume/cmd_vel', Twist, queue_size=10)
        self.gradient_pub = rospy.Publisher('/gas_plume/gradient', Point, queue_size=10)
        self.source_pub = rospy.Publisher('/gas_plume/source_estimate', Point, queue_size=10)
        self.state_pub = rospy.Publisher('/gas_plume/state', Float32MultiArray, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/gas_sensors', Float32MultiArray, self.gas_callback)
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        
        # Control timer
        self.control_timer = rospy.Timer(rospy.Duration(0.1), self.control_loop)
        
        rospy.loginfo("Gas Plume Tracker initialized")
    
    def gas_callback(self, msg):
        """Process gas sensor data"""
        if len(msg.data) > 0:
            self.current_concentration = msg.data[0]
            self.last_sensor_time = rospy.Time.now()
            
            # Store in history
            self.concentration_history.append(self.current_concentration)
            self.position_history.append(self.current_position.copy())
            self.time_history.append(rospy.Time.now())
            
            # Update peak
            if self.current_concentration > self.peak_concentration:
                self.peak_concentration = self.current_concentration
                self.source_estimate = self.current_position.copy()
    
    def odom_callback(self, msg):
        """Process odometry data"""
        self.current_position[0] = msg.pose.pose.position.x
        self.current_position[1] = msg.pose.pose.position.y
        
        # Extract yaw from quaternion
        orientation = msg.pose.pose.orientation
        siny_cosp = 2.0 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1.0 - 2.0 * (orientation.y ** 2 + orientation.z ** 2)
        self.current_yaw = math.atan2(siny_cosp, cosy_cosp)
    
    def estimate_gradient(self):
        """
        Estimate concentration gradient using spatial-temporal data
        Uses finite difference method with learning-based weighting
        """
        if len(self.concentration_history) < 3:
            return
        
        # Convert to numpy arrays
        concentrations = np.array(self.concentration_history)
        positions = np.array(self.position_history)
        
        # Calculate finite differences
        gradients = []
        weights = []
        
        for i in range(1, len(concentrations)):
            dc = concentrations[i] - concentrations[i-1]
            dx = positions[i][0] - positions[i-1][0]
            dy = positions[i][1] - positions[i-1][1]
            
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > 0.01:  # Avoid division by zero
                # Gradient components
                grad_x = dc * dx / (distance ** 2)
                grad_y = dc * dy / (distance ** 2)
                
                gradients.append([grad_x, grad_y])
                
                # Weight recent measurements more
                age = len(concentrations) - i
                weight = math.exp(-age / 5.0)
                weights.append(weight)
        
        if len(gradients) == 0:
            return
        
        # Weighted average of gradients
        gradients = np.array(gradients)
        weights = np.array(weights)
        weights = weights / np.sum(weights)  # Normalize
        
        self.gradient_vector = np.average(gradients, axis=0, weights=weights)
        self.gradient_magnitude = np.linalg.norm(self.gradient_vector)
        
        if self.gradient_magnitude > 0.001:
            self.gradient_direction = math.atan2(self.gradient_vector[1], self.gradient_vector[0])
        
        # Publish gradient
        grad_msg = Point()
        grad_msg.x = self.gradient_vector[0]
        grad_msg.y = self.gradient_vector[1]
        grad_msg.z = self.gradient_magnitude
        self.gradient_pub.publish(grad_msg)
    
    def update_state(self):
        """
        Bio-inspired state machine:
        - SEARCHING: Random walk when no plume detected
        - TRACKING: Follow gradient when plume detected and gradient available
        - CASTING: Crosswind search when plume lost
        - SURGE: Move upwind when strong gradient detected
        """
        # Check sensor timeout
        if self.last_sensor_time is None:
            self.state = 'SEARCHING'
            return
        
        time_since_reading = (rospy.Time.now() - self.last_sensor_time).to_sec()
        if time_since_reading > self.timeout:
            self.state = 'SEARCHING'
            return
        
        # Decision logic
        in_plume = self.current_concentration > self.plume_threshold
        has_gradient = self.gradient_magnitude > 0.01
        
        if not in_plume:
            # Lost plume - start casting
            if self.state == 'TRACKING' or self.state == 'SURGE':
                self.state = 'CASTING'
                rospy.loginfo("Plume lost - starting cast maneuver")
            elif self.state != 'CASTING':
                self.state = 'SEARCHING'
        else:
            # In plume
            if has_gradient:
                # Check if gradient is increasing (getting closer to source)
                recent_concentrations = list(self.concentration_history)[-5:]
                if len(recent_concentrations) >= 2:
                    trend = recent_concentrations[-1] - recent_concentrations[0]
                    if trend > 10.0:  # Strong increase
                        self.state = 'SURGE'
                    else:
                        self.state = 'TRACKING'
                else:
                    self.state = 'TRACKING'
            else:
                # In plume but no gradient yet
                self.state = 'TRACKING'
    
    def generate_command(self):
        """Generate velocity command based on current state"""
        twist = Twist()
        
        if self.state == 'SEARCHING':
            # Lévy flight inspired search pattern
            # Random walk with occasional long jumps
            if np.random.rand() < 0.1:  # 10% chance of direction change
                self.cast_direction = np.random.choice([-1.0, 1.0])
            
            twist.linear.x = 0.15
            twist.angular.z = self.cast_direction * 0.3
        
        elif self.state == 'TRACKING':
            # Follow gradient direction
            if self.gradient_magnitude > 0.01:
                # Calculate angle difference
                angle_to_gradient = self.normalize_angle(self.gradient_direction - self.current_yaw)
                
                # Proportional control
                twist.linear.x = 0.2
                twist.angular.z = 2.0 * angle_to_gradient
                
                # Adaptive learning: update optimal parameters
                if self.current_concentration > self.peak_concentration * 0.9:
                    self.optimal_surge_duration *= 1.01  # Increase slightly if successful
            else:
                # No gradient, slow down
                twist.linear.x = 0.1
                twist.angular.z = 0.0
        
        elif self.state == 'SURGE':
            # Aggressive upwind movement
            angle_to_gradient = self.normalize_angle(self.gradient_direction - self.current_yaw)
            
            twist.linear.x = self.surge_speed
            twist.angular.z = 3.0 * angle_to_gradient
            
            # Learn from success
            if self.current_concentration > self.peak_concentration:
                self.success_count += 1
                # Increase surge speed slightly
                self.surge_speed = min(0.5, self.surge_speed * 1.005)
        
        elif self.state == 'CASTING':
            # Crosswind zigzag search (moth-inspired)
            twist.linear.x = 0.15
            twist.angular.z = self.cast_direction * self.cast_angular_vel
            
            # Flip direction periodically
            if rospy.Time.now().to_sec() % self.optimal_cast_duration < 0.1:
                self.cast_direction *= -1.0
        
        return twist
    
    def normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def control_loop(self, event):
        """Main control loop"""
        # Estimate gradient
        self.estimate_gradient()
        
        # Update state
        self.update_state()
        
        # Generate command
        twist = self.generate_command()
        self.cmd_vel_pub.publish(twist)
        
        # Publish source estimate
        source_msg = Point()
        source_msg.x = self.source_estimate[0]
        source_msg.y = self.source_estimate[1]
        source_msg.z = self.peak_concentration
        self.source_pub.publish(source_msg)
        
        # Publish state info
        state_msg = Float32MultiArray()
        state_msg.data = [
            float(['SEARCHING', 'TRACKING', 'CASTING', 'SURGE'].index(self.state)),
            self.current_concentration,
            self.gradient_magnitude,
            self.peak_concentration,
            float(self.success_count),
            float(self.failure_count)
        ]
        self.state_pub.publish(state_msg)
    
    def run(self):
        """Main run method"""
        rospy.spin()


if __name__ == '__main__':
    try:
        tracker = GasPlumeTracker()
        tracker.run()
    except rospy.ROSInterruptException:
        pass
