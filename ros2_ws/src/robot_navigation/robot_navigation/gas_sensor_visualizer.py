#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray
from visualization_msgs.msg import Marker
from geometry_msgs.msg import Point

class GasSensorVisualizer(Node):
    def __init__(self):
        super().__init__('gas_sensor_visualizer')
        self.sensor_subscriber = self.create_subscription(
            Int32MultiArray,
            'gas_sensors',
            self.sensor_callback,
            10)
        self.marker_publisher = self.create_publisher(Marker, 'gas_sensor_marker', 10)
        self.marker = Marker()
        self.marker.header.frame_id = "base_link"  # Adjust to your robot's base frame
        self.marker.ns = "gas_sensor"
        self.marker.id = 0
        self.marker.type = Marker.SPHERE
        self.marker.action = Marker.ADD
        self.marker.pose.position.x = 1.0  # Relative to the base_link
        self.marker.pose.position.y = 0.0
        self.marker.pose.position.z = 0.5
        self.marker.pose.orientation.w = 1.0
        self.marker.scale.x = 0.2
        self.marker.scale.y = 0.2
        self.marker.scale.z = 0.2
        self.marker.color.a = 1.0
        self.marker.color.r = 0.0
        self.marker.color.g = 1.0
        self.marker.color.b = 0.0

    def sensor_callback(self, msg):
        mq2_val = msg.data[0]

        # Normalize gas value to a range between 0 and 1
        normalized_gas_value = min(1.0, max(0.0, mq2_val / 1000.0))  # Assuming max sensor value is 1000

        # Adjust marker color based on gas concentration
        self.marker.color.r = normalized_gas_value
        self.marker.color.g = 1.0 - normalized_gas_value
        self.marker.color.b = 0.0

        self.marker.header.stamp = self.get_clock().now().to_msg()
        self.marker_publisher.publish(self.marker)

def main(args=None):
    rclpy.init(args=args)
    gas_sensor_visualizer = GasSensorVisualizer()
    rclpy.spin(gas_sensor_visualizer)
    gas_sensor_visualizer.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()