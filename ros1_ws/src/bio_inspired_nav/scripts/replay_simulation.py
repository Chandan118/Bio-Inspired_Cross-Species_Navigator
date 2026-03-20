#!/usr/bin/env python3
"""
Replay Simulation in RViz
Reads CSV log file and publishes data to ROS topics for visualization
"""

import rospy
import csv
import sys
from nav_msgs.msg import Odometry
from geometry_msgs.msg import Point, Pose, Quaternion, Twist, Vector3
from sensor_msgs.msg import LaserScan, Imu, PointCloud2, PointField
from std_msgs.msg import Header
import tf
import math
import numpy as np
import struct

class SimulationReplayer:
    def __init__(self, csv_file, speed=1.0):
        rospy.init_node('simulation_replayer', anonymous=False)
        
        self.csv_file = csv_file
        self.speed = speed  # Playback speed multiplier
        
        # Publishers
        self.odom_pub = rospy.Publisher('/odom', Odometry, queue_size=10)
        self.scan_pub = rospy.Publisher('/scan', LaserScan, queue_size=10)
        self.imu_pub = rospy.Publisher('/imu', Imu, queue_size=10)
        self.pointcloud_pub = rospy.Publisher('/velodyne_points', PointCloud2, queue_size=10)
        self.tf_broadcaster = tf.TransformBroadcaster()
        
        rospy.loginfo("Simulation Replayer initialized")
        rospy.loginfo(f"Reading from: {csv_file}")
        rospy.loginfo(f"Playback speed: {speed}x")
    
    def generate_3d_lidar_pointcloud(self, x, y, yaw):
        """Generate 3D HDL-style LiDAR point cloud (Velodyne-like)"""
        points = []
        
        # HDL-64 style: 64 vertical layers
        num_layers = 32  # 32 layers for performance
        num_points_per_layer = 360  # 360 points per layer (1 degree resolution)
        
        # Vertical field of view: -15° to +15°
        vertical_fov_min = -15.0 * math.pi / 180.0
        vertical_fov_max = 15.0 * math.pi / 180.0
        
        for layer in range(num_layers):
            # Calculate vertical angle for this layer
            vertical_angle = vertical_fov_min + (vertical_fov_max - vertical_fov_min) * layer / (num_layers - 1)
            
            for i in range(num_points_per_layer):
                # Horizontal angle (360 degrees)
                horizontal_angle = (i * 2 * math.pi / num_points_per_layer)
                
                # Simulate realistic range with distance-dependent noise
                base_range = 5.0 + 3.0 * math.sin(horizontal_angle * 2 + x * 0.05)
                base_range += 2.0 * math.cos(vertical_angle * 3)
                
                # Add noise
                noise = np.random.normal(0, 0.05)
                range_val = max(0.5, min(30.0, base_range + noise))
                
                # Convert spherical to Cartesian coordinates
                point_x = range_val * math.cos(vertical_angle) * math.cos(horizontal_angle)
                point_y = range_val * math.cos(vertical_angle) * math.sin(horizontal_angle)
                point_z = range_val * math.sin(vertical_angle)
                
                # Intensity based on distance (closer = brighter)
                intensity = int(255 * (1.0 - range_val / 30.0))
                
                # RGB coloring based on height (like real Velodyne visualization)
                if point_z > 0.5:
                    rgb = struct.unpack('I', struct.pack('BBBB', 255, 100, 100, 255))[0]  # Red (high)
                elif point_z < -0.5:
                    rgb = struct.unpack('I', struct.pack('BBBB', 100, 100, 255, 255))[0]  # Blue (low)
                else:
                    rgb = struct.unpack('I', struct.pack('BBBB', 100, 255, 100, 255))[0]  # Green (mid)
                
                points.append([point_x, point_y, point_z, rgb, intensity])
        
        # Create PointCloud2 message
        header = Header()
        header.stamp = rospy.Time.now()
        header.frame_id = "velodyne"
        
        fields = [
            PointField('x', 0, PointField.FLOAT32, 1),
            PointField('y', 4, PointField.FLOAT32, 1),
            PointField('z', 8, PointField.FLOAT32, 1),
            PointField('rgb', 12, PointField.UINT32, 1),
            PointField('intensity', 16, PointField.FLOAT32, 1),
        ]
        
        # Pack point cloud data
        cloud_data = []
        for point in points:
            cloud_data.append(struct.pack('fffIf', point[0], point[1], point[2], point[3], point[4]))
        
        pointcloud = PointCloud2(
            header=header,
            height=1,
            width=len(points),
            is_dense=False,
            is_bigendian=False,
            fields=fields,
            point_step=20,  # 5 fields * 4 bytes
            row_step=20 * len(points),
            data=b''.join(cloud_data)
        )
        
        return pointcloud
    
    def generate_lidar_scan(self, x, y, yaw):
        """Generate simulated 3D LiDAR scan"""
        scan = LaserScan()
        scan.header = Header()
        scan.header.stamp = rospy.Time.now()
        scan.header.frame_id = "laser"
        
        scan.angle_min = -math.pi
        scan.angle_max = math.pi
        scan.angle_increment = math.pi / 180.0  # 1 degree
        scan.time_increment = 0.0
        scan.scan_time = 0.1
        scan.range_min = 0.1
        scan.range_max = 10.0
        
        # Generate simulated obstacles
        num_readings = 360
        ranges = []
        for i in range(num_readings):
            angle = scan.angle_min + i * scan.angle_increment
            # Simulate some obstacles at varying distances
            base_range = 5.0 + 2.0 * math.sin(angle * 3 + x * 0.1)
            noise = np.random.normal(0, 0.1)
            ranges.append(max(scan.range_min, min(scan.range_max, base_range + noise)))
        
        scan.ranges = ranges
        scan.intensities = [100.0] * num_readings
        return scan
    
    def generate_imu_data(self, yaw, angular_vel):
        """Generate IMU sensor data"""
        imu = Imu()
        imu.header = Header()
        imu.header.stamp = rospy.Time.now()
        imu.header.frame_id = "imu_link"
        
        # Orientation (from yaw)
        quat = tf.transformations.quaternion_from_euler(0, 0, yaw)
        imu.orientation = Quaternion(*quat)
        imu.orientation_covariance = [0.01, 0, 0, 0, 0.01, 0, 0, 0, 0.01]
        
        # Angular velocity
        imu.angular_velocity = Vector3(0, 0, angular_vel)
        imu.angular_velocity_covariance = [0.01, 0, 0, 0, 0.01, 0, 0, 0, 0.01]
        
        # Linear acceleration (simulated)
        imu.linear_acceleration = Vector3(
            np.random.normal(0, 0.1),
            np.random.normal(0, 0.1),
            9.81 + np.random.normal(0, 0.1)
        )
        imu.linear_acceleration_covariance = [0.01, 0, 0, 0, 0.01, 0, 0, 0, 0.01]
        
        return imu
        
    def replay(self):
        """Read CSV and publish odometry data"""
        rate = rospy.Rate(10 * self.speed)  # 10 Hz * speed
        
        with open(self.csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            prev_time = None
            count = 0
            
            rospy.loginfo("Starting playback...")
            
            for row in reader:
                if rospy.is_shutdown():
                    break
                
                try:
                    # Parse data
                    timestamp = float(row['timestamp'])
                    x = float(row['x'])
                    y = float(row['y'])
                    yaw = float(row['yaw'])
                    linear_vel = float(row['linear_vel'])
                    angular_vel = float(row['angular_vel'])
                    
                    # Create quaternion from yaw
                    quat = tf.transformations.quaternion_from_euler(0, 0, yaw)
                    
                    # Create odometry message
                    odom = Odometry()
                    odom.header = Header()
                    odom.header.stamp = rospy.Time.now()
                    odom.header.frame_id = "odom"
                    odom.child_frame_id = "base_footprint"
                    
                    # Set pose
                    odom.pose.pose = Pose(
                        Point(x, y, 0.0),
                        Quaternion(*quat)
                    )
                    
                    # Set velocity
                    odom.twist.twist = Twist(
                        Vector3(linear_vel, 0.0, 0.0),
                        Vector3(0.0, 0.0, angular_vel)
                    )
                    
                    # Publish
                    self.odom_pub.publish(odom)
                    
                    # Publish 3D HDL LiDAR point cloud
                    pointcloud = self.generate_3d_lidar_pointcloud(x, y, yaw)
                    self.pointcloud_pub.publish(pointcloud)
                    
                    # Publish 2D LiDAR scan (for compatibility)
                    scan = self.generate_lidar_scan(x, y, yaw)
                    self.scan_pub.publish(scan)
                    
                    # Publish IMU data
                    imu = self.generate_imu_data(yaw, angular_vel)
                    self.imu_pub.publish(imu)
                    
                    # Broadcast TF transforms
                    current_time = rospy.Time.now()
                    
                    # odom -> base_footprint
                    self.tf_broadcaster.sendTransform(
                        (x, y, 0.0),
                        quat,
                        current_time,
                        "base_footprint",
                        "odom"
                    )
                    
                    # base_footprint -> base_link
                    self.tf_broadcaster.sendTransform(
                        (0.0, 0.0, 0.1),
                        (0.0, 0.0, 0.0, 1.0),
                        current_time,
                        "base_link",
                        "base_footprint"
                    )
                    
                    # base_link -> laser
                    self.tf_broadcaster.sendTransform(
                        (0.2, 0.0, 0.2),
                        (0.0, 0.0, 0.0, 1.0),
                        current_time,
                        "laser",
                        "base_link"
                    )
                    
                    # base_link -> imu_link
                    self.tf_broadcaster.sendTransform(
                        (0.0, 0.0, 0.15),
                        (0.0, 0.0, 0.0, 1.0),
                        current_time,
                        "imu_link",
                        "base_link"
                    )
                    
                    # base_link -> velodyne (3D LiDAR)
                    self.tf_broadcaster.sendTransform(
                        (0.0, 0.0, 0.4),
                        (0.0, 0.0, 0.0, 1.0),
                        current_time,
                        "velodyne",
                        "base_link"
                    )
                    
                    count += 1
                    
                    if count % 1000 == 0:
                        rospy.loginfo(f"Published {count} poses... Position: ({x:.1f}, {y:.1f})")
                    
                    # Control playback rate
                    if prev_time is not None:
                        time_diff = timestamp - prev_time
                        rospy.sleep(time_diff / self.speed)
                    prev_time = timestamp
                    
                    rate.sleep()
                    
                except Exception as e:
                    rospy.logwarn(f"Error processing row: {e}")
                    continue
        
        rospy.loginfo(f"Playback complete! Published {count} poses")
        rospy.loginfo("You can now see the complete 19-hour path in RViz!")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        csv_file = '/tmp/bio_nav_logs/nav_log_20260101_121310.csv'
    else:
        csv_file = sys.argv[1]
    
    speed = 100.0 if len(sys.argv) < 3 else float(sys.argv[2])  # Default 100x speed
    
    try:
        replayer = SimulationReplayer(csv_file, speed)
        replayer.replay()
    except rospy.ROSInterruptException:
        pass
    except KeyboardInterrupt:
        rospy.loginfo("Playback stopped by user")
