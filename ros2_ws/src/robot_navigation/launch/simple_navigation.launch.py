#!/usr/bin/env python3
"""
Simple navigation launch file for testing without external hardware dependencies
"""

from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        # Navigator Node
        Node(
            package='robot_navigation',
            executable='navigator',
            name='navigator_node',
            output='screen',
            parameters=[{
                'obstacle_distance': 0.5,
                'forward_speed': 0.2,
                'turn_speed': 0.5,
                'gas_threshold': 500,
                'kp': 1.0,
                'ki': 0.0,
                'kd': 0.0
            }]
        ),
        
        # Base Controller Node (will handle Arduino connection errors gracefully)
        Node(
            package='robot_navigation',
            executable='base_controller',
            name='base_controller_node',
            output='screen',
            parameters=[{
                'arduino_port': '/dev/ttyACM0',
                'wheel_base': 0.5,
                'wheel_radius': 0.1
            }]
        ),
        
        # Gas Sensor Visualizer Node
        Node(
            package='robot_navigation',
            executable='gas_sensor_visualizer',
            name='gas_sensor_visualizer',
            output='screen'
        ),
        
        # Camera Publisher Node (will handle camera errors gracefully)
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
