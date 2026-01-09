#!/usr/bin/env python3
"""
Working navigation launch file with mock sensors for demonstration
"""

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Mock Sensors Node (provides fake LiDAR and IMU data)
        Node(
            package='robot_navigation',
            executable='mock_sensors',
            name='mock_sensors_node',
            output='screen'
        ),
        
        # Mock Arduino Node (simulates motor control and gas sensors)
        Node(
            package='robot_navigation',
            executable='mock_arduino',
            name='mock_arduino_node',
            output='screen'
        ),
        
        # Navigator Node
        Node(
            package='robot_navigation',
            executable='navigator',
            name='navigator_node',
            output='screen',
            parameters=[{
                'obstacle_distance': 2.0,  # Increased distance for clear path
                'forward_speed': 0.3,
                'turn_speed': 0.5,
                'gas_threshold': 500,
                'kp': 1.0,
                'ki': 0.0,
                'kd': 0.0
            }]
        ),
        
        # Gas Sensor Visualizer Node
        Node(
            package='robot_navigation',
            executable='gas_sensor_visualizer',
            name='gas_sensor_visualizer',
            output='screen'
        ),
        
        # Optional: Camera Publisher (will fail gracefully if no camera)
        Node(
            package='robot_navigation',
            executable='camera_publisher',
            name='camera_publisher',
            output='screen',
            parameters=[{
                'gstreamer_pipeline': 'v4l2src device=/dev/video0 ! video/x-raw, width=640, height=480, framerate=15/1 ! videoconvert ! video/x-raw, format=BGR ! appsink drop=true',
                'frame_rate': 15.0,
                'topic_name': 'camera/image_raw',
                'frame_id': 'camera_frame'
            }]
        )
    ])
