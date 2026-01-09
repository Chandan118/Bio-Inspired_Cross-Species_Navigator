#!/usr/bin/env python3
import cv2
import numpy as np
import rclpy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from rclpy.node import Node

# GStreamer pipeline for a USB camera (/dev/video0)
# This pipeline is optimized for Jetson, using hardware-accelerated video conversion.
# It captures raw video, converts it to a format the GPU understands (NVMM memory),
# and then converts it to BGR for OpenCV.
USB_GSTREAMER_PIPELINE = (
    'v4l2src device=/dev/video0 ! '
    'video/x-raw, width=1280, height=720, framerate=30/1 ! '
    'videoconvert ! '
    'video/x-raw, format=BGR ! appsink drop=true'
)

# GStreamer pipeline for a CSI camera (e.g., Raspberry Pi Camera Module v2)
# This uses the NVIDIA nvarguscamerasrc plugin for direct, efficient camera access.
# This pipeline might require modification depending on the camera and Jetson configuration.
CSI_GSTREAMER_PIPELINE = (
    'nvarguscamerasrc sensor-id=0 ! '
    'video/x-raw(memory:NVMM), width=1920, height=1080, framerate=30/1, format=NV12 ! '
    'nvvidconv flip-method=0 ! '
    'video/x-raw, width=1280, height=720, format=BGRx ! '
    'videoconvert ! '
    'video/x-raw, format=BGR ! appsink drop=true'
)

class JetsonCameraPublisher(Node):
    """
    A ROS2 node that captures video from a camera using a GStreamer pipeline
    and publishes it. Optimized for NVIDIA Jetson platforms.
    """
    def __init__(self):
        super().__init__('jetson_camera_publisher')

        # Declare parameters
        # The default is set for a USB camera at /dev/video0.
        # You can override this with a launch file or command-line argument.
        self.declare_parameter('gstreamer_pipeline', USB_GSTREAMER_PIPELINE)
        self.declare_parameter('frame_rate', 30.0)
        self.declare_parameter('topic_name', 'camera/image_raw')
        self.declare_parameter('frame_id', 'camera_frame')
        self.declare_parameter('allow_mock_camera', True)
        self.declare_parameter('mock_frame_resolution', [640, 480])

        # Get parameters
        pipeline = self.get_parameter('gstreamer_pipeline').get_parameter_value().string_value
        frame_rate = self.get_parameter('frame_rate').get_parameter_value().double_value
        topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        self.frame_id = self.get_parameter('frame_id').get_parameter_value().string_value
        self.allow_mock = self.get_parameter('allow_mock_camera').get_parameter_value().bool_value
        mock_resolution_param = self.get_parameter('mock_frame_resolution').get_parameter_value()
        self.mock_resolution = list(mock_resolution_param.integer_array_value) or [640, 480]

        # Create the publisher
        self.publisher_ = self.create_publisher(Image, topic_name, 10)
        
        # Create a timer that fires at the specified frame rate
        timer_period = 1.0 / frame_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        # Initialize OpenCV VideoCapture with the GStreamer pipeline
        self.cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        self.mock_mode = False

        if not self.cap.isOpened():
            if self.allow_mock:
                self.mock_mode = True
                self.cap.release()
                self.cap = None
                self.get_logger().warning(
                    'Could not open camera with configured GStreamer pipeline; '
                    'falling back to synthetic frames. Check whether the device is busy '
                    'or update the gstreamer_pipeline parameter.'
                )
            else:
                self.get_logger().error("Could not open camera with GStreamer pipeline.")
                self.get_logger().error(f"Pipeline: {pipeline}")
                raise RuntimeError("Could not open camera")

        self.bridge = CvBridge()
        self.get_logger().info(f"Jetson camera publisher started.")
        self.get_logger().info(f"Publishing to topic '{topic_name}'")

    def timer_callback(self):
        """
        Reads a frame from the camera, converts it, and publishes it.
        """
        if self.mock_mode:
            frame = self._generate_mock_frame()
            ret = True
        else:
            ret, frame = self.cap.read()

        if ret and frame is not None:
            # Convert the OpenCV image (BGR) to a ROS Image message
            ros_image_msg = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8") # Specify encoding

            # Set the timestamp and frame_id
            ros_image_msg.header.stamp = self.get_clock().now().to_msg()
            ros_image_msg.header.frame_id = self.frame_id
            
            self.publisher_.publish(ros_image_msg)
        else:
            self.get_logger().warn("Could not read frame from camera. The pipeline may be broken.")

    def on_shutdown(self):
        """
        Cleanup resources.
        """
        self.get_logger().info("Shutting down, releasing camera.")
        if self.cap is not None:
            self.cap.release()

    def _generate_mock_frame(self):
        width = max(2, int(self.mock_resolution[0]))
        height = max(2, int(self.mock_resolution[1]))
        # Create a simple gradient image with timestamp overlay colour changes for debugging.
        x = np.linspace(0, 255, width, dtype=np.uint8)
        gradient = np.tile(x, (height, 1))
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[..., 0] = gradient
        frame[..., 1] = np.flipud(gradient)
        now = int(self.get_clock().now().nanoseconds / 1e6) % 255
        frame[..., 2] = now
        return frame


def main(args=None):
    rclpy.init(args=args)
    camera_publisher = None
    try:
        camera_publisher = JetsonCameraPublisher()
        rclpy.spin(camera_publisher)
    except KeyboardInterrupt:
        if camera_publisher:
            camera_publisher.get_logger().info("Keyboard interrupt, shutting down.")
    except RuntimeError:
        # The error is logged in the constructor.
        pass
    finally:
        if camera_publisher:
            camera_publisher.on_shutdown()
            camera_publisher.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
