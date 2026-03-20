from setuptools import setup, find_packages
import os
from glob import glob

package_name = 'robot_navigation'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    # package_dir={'': 'src'}, # This line is not needed if your code is in a folder named after the package
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@todo.todo',
    description='Bio-Inspired Cross-Species Navigator ROS 2 Package',
    license='MIT',
    extras_require={'test': ['pytest']},
    entry_points={
        'console_scripts': [
            'base_controller = robot_navigation.base_controller_node:main',
            'navigator = robot_navigation.navigator_node:main',
            'gas_sensor_visualizer = robot_navigation.gas_sensor_visualizer:main',
            'camera_publisher = robot_navigation.camera_publisher:main',
            'vision_processor = robot_navigation.vision_processor_node:main',
            'mission_manager = robot_navigation.mission_manager_node:main',
            'mock_sensors = robot_navigation.mock_sensors_node:main',
            'mock_arduino = robot_navigation.mock_arduino_node:main',
        ],
    },
)
