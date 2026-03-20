import os
from ament_index_python.packages import (
    PackageNotFoundError,
    get_package_share_directory,
)
from launch import LaunchDescription, logging
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    description_actions = []
    logger = logging.get_logger('start_navigation_launch')

    # Try to include the RPLIDAR launch file if the package is available.
    try:
        rplidar_ros_path = get_package_share_directory('rplidar_ros')
        rplidar_launch_file = os.path.join(
            rplidar_ros_path,
            'launch',
            'rplidar.launch.py',
        )
        description_actions.append(
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(rplidar_launch_file),
                launch_arguments={
                    'serial_port': '/dev/ttyUSB0',
                    'serial_baudrate': '115200',
                    'frame_id': 'laser_frame',
                    'angle_compensate': 'true',
                }.items(),
            )
        )
    except PackageNotFoundError:
        logger.warning(
            "Package 'rplidar_ros' not found. Skipping RPLIDAR launch include. "
            "Install rplidar_ros or add it to the workspace if the sensor is required."
        )

    try:
        # We only need to know the package exists; no direct path usage required.
        get_package_share_directory('lpms_ig1')
        description_actions.extend(
            [
                Node(
                    namespace='imu',
                    package='lpms_ig1',
                    executable='lpms_ig1_node',
                    output='screen',
                    parameters=[
                        {
                            "port": "/dev/ttyUSB1",
                            "baudrate": 115200,
                        }
                    ],
                ),
                Node(
                    namespace='imu',
                    package='lpms_ig1',
                    executable='quat_to_euler_node',
                    output='screen',
                ),
            ]
        )
    except PackageNotFoundError:
        logger.warning(
            "Package 'lpms_ig1' not found. Skipping IMU nodes. "
            "Install lpms_ig1 or add it to the workspace if the sensor is required."
        )

    description_actions.extend(
        [
            Node(
                package='robot_navigation',
                executable='camera_publisher',
                name='camera_node',
                output='screen',
            ),
            Node(
                package='robot_navigation',
                executable='vision_processor',
                name='vision_processor',
                output='screen',
                parameters=[
                    {
                        'target_hue': 20.0,
                        'target_hue_tolerance': 18.0,
                        'target_saturation_min': 70.0,
                        'target_value_min': 70.0,
                        'min_contour_area': 1200.0,
                        'blur_kernel': 5,
                        'morph_kernel': 5,
                        'debug': False,
                    }
                ],
            ),
            Node(
                package='robot_navigation',
                executable='base_controller',
                name='base_controller_node',
                output='screen',
                parameters=[
                    {
                        'arduino_port': '/dev/ttyCH341USB0',
                        'fallback_ports': [
                            '/dev/ttyCH341USB0',
                            '/dev/ttyUSB0',
                            '/dev/ttyUSB1',
                            '/dev/ttyACM0',
                            '/dev/ttyACM1',
                        ],
                        'baud_rate': 9600,
                        'motor_command_mode': 'simple',
                        'sensor_poll_interval': 1.0,
                        'sensor_command_sequence': ['M', 'C', 'O', 'U'],
                    }
                ],
            ),
            Node(
                package='robot_navigation',
                executable='navigator',
                name='navigator_node',
                output='screen',
                parameters=[
                    {
                        'obstacle_front_distance': 0.6,
                        'obstacle_side_distance': 0.45,
                        'explore_forward_speed': 0.22,
                        'track_forward_speed': 0.16,
                        'approach_forward_speed': 0.28,
                        'avoid_turn_speed': 0.7,
                        'vision_steering_gain': 1.5,
                        'vision_timeout': 2.5,
                        'scent_threshold_increase': 35.0,
                        'scent_timeout': 6.0,
                        'scent_turn_rate': 0.45,
                        'explore_heading_interval': 8.0,
                    }
                ],
            ),
        ]
    )

    return LaunchDescription(description_actions)
