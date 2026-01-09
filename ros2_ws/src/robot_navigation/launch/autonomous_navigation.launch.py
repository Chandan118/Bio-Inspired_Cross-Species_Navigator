#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    robot_navigation_dir = get_package_share_directory('robot_navigation')
    nav2_params = os.path.join(robot_navigation_dir, 'config', 'nav2_params.yaml')
    slam_params = os.path.join(robot_navigation_dir, 'config', 'slam_toolbox.yaml')
    localization_params = os.path.join(robot_navigation_dir, 'config', 'localization.yaml')
    default_map = os.path.join(
        get_package_share_directory('nav2_bringup'),
        'maps',
        'turtlebot3_world.yaml',
    )

    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    use_sim_time = LaunchConfiguration('use_sim_time')
    enable_slam = LaunchConfiguration('enable_slam')
    nav2_params_file = LaunchConfiguration('nav2_params_file')
    slam_params_file = LaunchConfiguration('slam_params_file')
    localization_params_file = LaunchConfiguration('localization_params_file')
    waypoints_yaml = LaunchConfiguration('waypoints_yaml')
    map_file = LaunchConfiguration('map')

    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    )

    declare_enable_slam = DeclareLaunchArgument(
        'enable_slam',
        default_value='true',
        description='Run SLAM Toolbox (true) or assume an existing map (false).'
    )

    declare_nav2_params = DeclareLaunchArgument(
        'nav2_params_file',
        default_value=nav2_params,
        description='Full path to the Nav2 parameter file to use'
    )

    declare_slam_params = DeclareLaunchArgument(
        'slam_params_file',
        default_value=slam_params,
        description='Full path to the SLAM Toolbox parameter file'
    )

    declare_localization_params = DeclareLaunchArgument(
        'localization_params_file',
        default_value=localization_params,
        description='Full path to the robot_localization configuration'
    )

    declare_waypoints_yaml = DeclareLaunchArgument(
        'waypoints_yaml',
        default_value='[]',
        description='YAML-encoded array of mission waypoints.'
    )

    declare_map = DeclareLaunchArgument(
        'map',
        default_value=default_map,
        description='Full path to the map YAML file used by Nav2 (required even when SLAM is enabled).',
    )

    slam_toolbox_node = Node(
        condition=IfCondition(enable_slam),
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[slam_params_file, {'use_sim_time': use_sim_time}],
    )

    robot_localization_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[localization_params_file, {'use_sim_time': use_sim_time}],
    )

    navsat_transform_node = Node(
        package='robot_localization',
        executable='navsat_transform_node',
        name='navsat_transform',
        output='screen',
        parameters=[localization_params_file, {'use_sim_time': use_sim_time}],
        remappings=[
            ('imu/data', 'imu/data'),
            ('gps/fix', 'gps/fix'),
            ('odometry/filtered', 'odometry/global'),
        ],
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'slam': enable_slam,
            'params_file': nav2_params_file,
            'use_composition': 'False',
            'autostart': 'True',
            'map': map_file,
        }.items(),
    )

    base_controller_node = Node(
        package='robot_navigation',
        executable='base_controller',
        name='base_controller_node',
        output='screen',
    )

    camera_node = Node(
        package='robot_navigation',
        executable='camera_publisher',
        name='camera_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    vision_processor_node = Node(
        package='robot_navigation',
        executable='vision_processor',
        name='vision_processor',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
    )

    mission_manager_node = Node(
        package='robot_navigation',
        executable='mission_manager',
        name='mission_manager',
        output='screen',
        parameters=[{'waypoints_yaml': waypoints_yaml}],
    )

    ld = LaunchDescription()
    ld.add_action(declare_use_sim_time)
    ld.add_action(declare_enable_slam)
    ld.add_action(declare_nav2_params)
    ld.add_action(declare_slam_params)
    ld.add_action(declare_localization_params)
    ld.add_action(declare_waypoints_yaml)
    ld.add_action(declare_map)

    ld.add_action(slam_toolbox_node)
    ld.add_action(robot_localization_node)
    ld.add_action(navsat_transform_node)
    ld.add_action(nav2_launch)

    ld.add_action(base_controller_node)
    ld.add_action(camera_node)
    ld.add_action(vision_processor_node)
    ld.add_action(mission_manager_node)

    return ld
