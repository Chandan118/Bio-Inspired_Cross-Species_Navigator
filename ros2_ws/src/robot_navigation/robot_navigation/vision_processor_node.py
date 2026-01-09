#!/usr/bin/env python3
import math

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32


class VisionProcessor(Node):
    """
    Lightweight vision processor for dog-inspired navigation.

    The node tracks a configurable colour signature (default: warm orange) and publishes:
      - vision/target_detected (Bool)
      - vision/target_offset (Float32, normalised horizontal offset [-1, 1])

    Downstream consumers can steer towards the target when detection is true.
    """

    def __init__(self):
        super().__init__('vision_processor')

        # Parameters describing the target colour in HSV space
        self.declare_parameter('target_hue', 20.0)            # Approx. orange / warm tone
        self.declare_parameter('target_hue_tolerance', 15.0)
        self.declare_parameter('target_saturation_min', 80.0)
        self.declare_parameter('target_value_min', 80.0)
        self.declare_parameter('min_contour_area', 1500.0)
        self.declare_parameter('blur_kernel', 5)
        self.declare_parameter('morph_kernel', 5)
        self.declare_parameter('debug', False)

        self.bridge = CvBridge()

        self.image_sub = self.create_subscription(
            Image,
            'camera/image_raw',
            self.image_callback,
            10,
        )
        self.detected_pub = self.create_publisher(Bool, 'vision/target_detected', 10)
        self.offset_pub = self.create_publisher(Float32, 'vision/target_offset', 10)

        self.debug_image_pub = None
        if self.get_parameter('debug').value:
            self.debug_image_pub = self.create_publisher(Image, 'vision/debug_image', 1)

    def image_callback(self, msg: Image):
        try:
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as exc:
            self.get_logger().warning(f'Failed to convert image: {exc}')
            return

        height, width = frame.shape[:2]
        if width == 0 or height == 0:
            return

        blur_kernel = int(max(1, self.get_parameter('blur_kernel').value))
        if blur_kernel % 2 == 0:
            blur_kernel += 1
        blurred = cv2.GaussianBlur(frame, (blur_kernel, blur_kernel), 0)

        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        hue_center = self.get_parameter('target_hue').value
        hue_tol = self.get_parameter('target_hue_tolerance').value
        sat_min = self.get_parameter('target_saturation_min').value
        val_min = self.get_parameter('target_value_min').value

        lower = np.array([
            max(0, hue_center - hue_tol),
            sat_min,
            val_min,
        ], dtype=np.uint8)
        upper = np.array([
            min(179, hue_center + hue_tol),
            255,
            255,
        ], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower, upper)

        morph_size = int(max(1, self.get_parameter('morph_kernel').value))
        kernel = np.ones((morph_size, morph_size), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = self.get_parameter('min_contour_area').value

        detected = False
        offset = 0.0
        best_contour = None
        best_area = 0.0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area and area > best_area:
                best_area = area
                best_contour = contour

        if best_contour is not None:
            moments = cv2.moments(best_contour)
            if moments['m00'] != 0:
                cx = int(moments['m10'] / moments['m00'])
                offset = 2.0 * ((cx / width) - 0.5)  # normalised bearing
                detected = True
                if self.debug_image_pub:
                    cv2.drawContours(frame, [best_contour], -1, (0, 255, 0), 2)
                    cv2.circle(frame, (cx, height // 2), 5, (0, 0, 255), -1)

        self.detected_pub.publish(Bool(data=detected))
        self.offset_pub.publish(Float32(data=offset))

        if self.debug_image_pub:
            debug_msg = self.bridge.cv2_to_imgmsg(frame, encoding='bgr8')
            debug_msg.header = msg.header
            self.debug_image_pub.publish(debug_msg)


def main(args=None):
    rclpy.init(args=args)
    node = VisionProcessor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Vision processor interrupted by user.')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
