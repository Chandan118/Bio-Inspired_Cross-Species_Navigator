#!/usr/bin/env python3

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    channel_type = LaunchConfiguration('channel_type')
    serial_port = LaunchConfiguration('serial_port')
    serial_baudrate = LaunchConfiguration('serial_baudrate')
    frame_id = LaunchConfiguration('frame_id')
    inverted = LaunchConfiguration('inverted')
    angle_compensate = LaunchConfiguration('angle_compensate')
    scan_mode = LaunchConfiguration('scan_mode')

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                'channel_type',
                default_value='serial',
                description='Connection type for the RPLIDAR (serial or tcp).',
            ),
            DeclareLaunchArgument(
                'serial_port',
                default_value='/dev/ttyUSB0',
                description='Serial port used to connect the RPLIDAR.',
            ),
            DeclareLaunchArgument(
                'serial_baudrate',
                default_value='115200',
                description='Baud rate for the serial connection.',
            ),
            DeclareLaunchArgument(
                'frame_id',
                default_value='laser',
                description='Frame id for published LaserScan messages.',
            ),
            DeclareLaunchArgument(
                'inverted',
                default_value='false',
                description='Invert the scan data if true.',
            ),
            DeclareLaunchArgument(
                'angle_compensate',
                default_value='true',
                description='Enable angle compensation on the scan data.',
            ),
            DeclareLaunchArgument(
                'scan_mode',
                default_value='Sensitivity',
                description='Requested scan mode (depends on RPLIDAR model).',
            ),
            Node(
                package='rplidar_ros',
                executable='rplidar_node',
                name='rplidar_node',
                output='screen',
                parameters=[
                    {
                        'channel_type': channel_type,
                        'serial_port': serial_port,
                        'serial_baudrate': serial_baudrate,
                        'frame_id': frame_id,
                        'inverted': inverted,
                        'angle_compensate': angle_compensate,
                        'scan_mode': scan_mode,
                    }
                ],
            ),
        ]
    )
