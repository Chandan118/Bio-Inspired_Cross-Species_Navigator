#!/usr/bin/env python3
"""
Data Logger for Bio-Inspired Navigation
Logs all sensor data, navigation states, and performance metrics
"""

import rospy
import csv
import os
from datetime import datetime
from std_msgs.msg import Float32MultiArray, Bool
from geometry_msgs.msg import Twist, Point
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
import matplotlib.pyplot as plt
import numpy as np


class DataLogger:
    """Comprehensive data logging and real-time plotting"""
    
    def __init__(self):
        rospy.init_node('data_logger', anonymous=True)
        
        # Log directory
        log_dir = rospy.get_param('~log_dir', '/tmp/bio_nav_logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Create timestamped log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = os.path.join(log_dir, 'nav_log_' + timestamp + '.csv')
        
        # CSV writer
        self.csv_file = open(self.log_file, 'w', newline='')
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            'timestamp', 'x', 'y', 'yaw', 'linear_vel', 'angular_vel',
            'gas_concentration', 'gas_gradient', 'distance_to_source',
            'min_obstacle_dist', 'vision_detected', 'vision_offset',
            'plume_state', 'nav_state', 'total_distance'
        ])
        
        # Data storage for plotting
        self.data = {
            'time': [],
            'x': [],
            'y': [],
            'gas': [],
            'distance_to_source': [],
            'velocity': [],
            'reward': []
        }
        
        # Current values
        self.current_time = 0.0
        self.odom_x = 0.0
        self.odom_y = 0.0
        self.odom_yaw = 0.0
        self.linear_vel = 0.0
        self.angular_vel = 0.0
        self.gas_concentration = 0.0
        self.gas_gradient = 0.0
        self.distance_to_source = 0.0
        self.min_obstacle_dist = 10.0
        self.vision_detected = False
        self.vision_offset = 0.0
        self.plume_state = 0.0
        self.nav_state = 0.0
        self.total_distance = 0.0
        self.prev_x = 0.0
        self.prev_y = 0.0
        
        # Plotting
        self.plot_enabled = rospy.get_param('~enable_plotting', True)
        if self.plot_enabled:
            plt.ion()
            self.fig, self.axes = plt.subplots(2, 2, figsize=(12, 8))
            self.fig.suptitle('Bio-Inspired Navigation - Real-time Metrics')
        
        # Subscribers
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        rospy.Subscriber('/cmd_vel', Twist, self.cmd_vel_callback)
        rospy.Subscriber('/gas_sensors', Float32MultiArray, self.gas_callback)
        rospy.Subscriber('/scan', LaserScan, self.scan_callback)
        rospy.Subscriber('/vision/target_detected', Bool, self.vision_callback)
        rospy.Subscriber('/vision/target_offset', Float32MultiArray, self.vision_offset_callback)
        rospy.Subscriber('/gas_plume/state', Float32MultiArray, self.plume_state_callback)
        rospy.Subscriber('/navigator/state', Float32MultiArray, self.nav_state_callback)
        
        # Logging timer
        self.log_timer = rospy.Timer(rospy.Duration(0.5), self.log_data)
        
        # Plotting timer
        if self.plot_enabled:
            self.plot_timer = rospy.Timer(rospy.Duration(2.0), self.update_plots)
        
        rospy.loginfo("Data Logger initialized. Logging to: " + self.log_file)
    
    def odom_callback(self, msg):
        """Store odometry data"""
        self.odom_x = msg.pose.pose.position.x
        self.odom_y = msg.pose.pose.position.y
        
        # Extract yaw
        orientation = msg.pose.pose.orientation
        siny_cosp = 2.0 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1.0 - 2.0 * (orientation.y ** 2 + orientation.z ** 2)
        self.odom_yaw = np.arctan2(siny_cosp, cosy_cosp)
        
        # Calculate distance traveled
        dx = self.odom_x - self.prev_x
        dy = self.odom_y - self.prev_y
        self.total_distance += np.sqrt(dx**2 + dy**2)
        self.prev_x = self.odom_x
        self.prev_y = self.odom_y
    
    def cmd_vel_callback(self, msg):
        """Store velocity commands"""
        self.linear_vel = msg.linear.x
        self.angular_vel = msg.angular.z
    
    def gas_callback(self, msg):
        """Store gas sensor data"""
        if len(msg.data) >= 5:
            self.gas_concentration = msg.data[0]
            self.gas_gradient = msg.data[1]
            self.distance_to_source = msg.data[4]
    
    def scan_callback(self, msg):
        """Store minimum obstacle distance"""
        if len(msg.ranges) > 0:
            valid_ranges = [r for r in msg.ranges if msg.range_min <= r <= msg.range_max]
            self.min_obstacle_dist = min(valid_ranges) if valid_ranges else 10.0
    
    def vision_callback(self, msg):
        """Store vision detection status"""
        self.vision_detected = msg.data
    
    def vision_offset_callback(self, msg):
        """Store vision offset"""
        if len(msg.data) > 0:
            self.vision_offset = msg.data[0]
    
    def plume_state_callback(self, msg):
        """Store gas plume tracker state"""
        if len(msg.data) > 0:
            self.plume_state = msg.data[0]
    
    def nav_state_callback(self, msg):
        """Store navigator state"""
        if len(msg.data) > 0:
            self.nav_state = msg.data[0]
    
    def log_data(self, event):
        """Write current data to CSV"""
        self.current_time = rospy.Time.now().to_sec()
        
        # Write to CSV
        self.csv_writer.writerow([
            self.current_time,
            self.odom_x,
            self.odom_y,
            self.odom_yaw,
            self.linear_vel,
            self.angular_vel,
            self.gas_concentration,
            self.gas_gradient,
            self.distance_to_source,
            self.min_obstacle_dist,
            int(self.vision_detected),
            self.vision_offset,
            self.plume_state,
            self.nav_state,
            self.total_distance
        ])
        self.csv_file.flush()
        
        # Store for plotting
        self.data['time'].append(self.current_time)
        self.data['x'].append(self.odom_x)
        self.data['y'].append(self.odom_y)
        self.data['gas'].append(self.gas_concentration)
        self.data['distance_to_source'].append(self.distance_to_source)
        self.data['velocity'].append(np.sqrt(self.linear_vel**2 + self.angular_vel**2))
        
        # Keep only last 1000 points
        if len(self.data['time']) > 1000:
            for key in self.data:
                self.data[key] = self.data[key][-1000:]
    
    def update_plots(self, event):
        """Update real-time plots"""
        if len(self.data['time']) < 2:
            return
        
        # Clear all subplots
        for ax in self.axes.flat:
            ax.clear()
        
        # Plot 1: Trajectory
        self.axes[0, 0].plot(self.data['x'], self.data['y'], 'b-', linewidth=2, label='Trajectory')
        self.axes[0, 0].plot(self.data['x'][-1], self.data['y'][-1], 'ro', markersize=10, label='Current')
        self.axes[0, 0].plot(8.0, 8.0, 'g*', markersize=15, label='Target')
        self.axes[0, 0].set_xlabel('X Position (m)')
        self.axes[0, 0].set_ylabel('Y Position (m)')
        self.axes[0, 0].set_title('Robot Trajectory')
        self.axes[0, 0].grid(True)
        self.axes[0, 0].legend()
        self.axes[0, 0].axis('equal')
        
        # Plot 2: Gas Concentration over time
        self.axes[0, 1].plot(self.data['time'], self.data['gas'], 'g-', linewidth=2)
        self.axes[0, 1].set_xlabel('Time (s)')
        self.axes[0, 1].set_ylabel('Gas Concentration')
        self.axes[0, 1].set_title('Gas Sensor Reading')
        self.axes[0, 1].grid(True)
        
        # Plot 3: Distance to source over time
        self.axes[1, 0].plot(self.data['time'], self.data['distance_to_source'], 'r-', linewidth=2)
        self.axes[1, 0].set_xlabel('Time (s)')
        self.axes[1, 0].set_ylabel('Distance to Source (m)')
        self.axes[1, 0].set_title('Distance to Gas Source')
        self.axes[1, 0].grid(True)
        
        # Plot 4: Velocity over time
        self.axes[1, 1].plot(self.data['time'], self.data['velocity'], 'm-', linewidth=2)
        self.axes[1, 1].set_xlabel('Time (s)')
        self.axes[1, 1].set_ylabel('Velocity (m/s)')
        self.axes[1, 1].set_title('Robot Velocity')
        self.axes[1, 1].grid(True)
        
        plt.tight_layout()
        plt.pause(0.01)
    
    def generate_summary(self):
        """Generate summary statistics"""
        if len(self.data['time']) < 2:
            return
        
        rospy.loginfo("="*60)
        rospy.loginfo("SIMULATION SUMMARY")
        rospy.loginfo("="*60)
        rospy.loginfo("Total simulation time: {:.2f} seconds".format(self.data['time'][-1] - self.data['time'][0]))
        rospy.loginfo("Total distance traveled: {:.2f} meters".format(self.total_distance))
        rospy.loginfo("Final distance to source: {:.2f} meters".format(self.data['distance_to_source'][-1]))
        rospy.loginfo("Minimum distance reached: {:.2f} meters".format(min(self.data['distance_to_source'])))
        rospy.loginfo("Peak gas concentration: {:.2f}".format(max(self.data['gas'])))
        rospy.loginfo("Average velocity: {:.3f} m/s".format(np.mean(self.data['velocity'])))
        rospy.loginfo("Data logged to: " + self.log_file)
        rospy.loginfo("="*60)
    
    def shutdown(self):
        """Clean up on shutdown"""
        self.generate_summary()
        self.csv_file.close()
        if self.plot_enabled:
            plt.savefig(self.log_file.replace('.csv', '_plots.png'))
            rospy.loginfo("Plots saved to: " + self.log_file.replace('.csv', '_plots.png'))
        rospy.loginfo("Data logger shutdown complete")
    
    def run(self):
        """Main loop"""
        rospy.on_shutdown(self.shutdown)
        rospy.spin()


if __name__ == '__main__':
    try:
        logger = DataLogger()
        logger.run()
    except rospy.ROSInterruptException:
        pass
