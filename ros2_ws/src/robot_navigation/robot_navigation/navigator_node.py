#!/usr/bin/env python3
import math
import random
from collections import deque

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from sensor_msgs.msg import Imu, LaserScan
from std_msgs.msg import Float32, Int32MultiArray, Bool


def wrap_angle(angle):
    """Wrap an angle to [-pi, pi]."""
    return math.atan2(math.sin(angle), math.cos(angle))


class Navigator(Node):
    """
    Multimodal navigator that blends lidar, IMU, gas sensors, and vision detections.

    Behaviour overview (dog inspired):
    - Explore by default, keeping a drift-corrected heading with periodic curiosity turns.
    - When scent intensity rises, slow down and weave to stay within the plume.
    - If the camera confirms a visual target, approach while steering towards the bearing.
    - Lidar and ultrasonic readings take precedence to avoid collisions.
    """

    def __init__(self):
        super().__init__('navigator')
        self.get_logger().info('Navigator Node Started')

        # Command publisher
        self.cmd_vel_publisher = self.create_publisher(Twist, 'cmd_vel', 10)

        # Sensor subscribers
        self.create_subscription(Imu, 'imu/data', self.imu_callback, 20)
        self.create_subscription(LaserScan, 'scan', self.scan_callback, 20)
        self.create_subscription(Int32MultiArray, 'gas_sensors', self.gas_callback, 20)
        self.create_subscription(Bool, 'vision/target_detected', self.vision_detected_callback, 10)
        self.create_subscription(Float32, 'vision/target_offset', self.vision_offset_callback, 10)

        # Parameters governing behaviour
        self.declare_parameter('obstacle_front_distance', 0.6)
        self.declare_parameter('obstacle_side_distance', 0.4)
        self.declare_parameter('obstacle_clear_time', 1.5)
        self.declare_parameter('explore_forward_speed', 0.22)
        self.declare_parameter('track_forward_speed', 0.16)
        self.declare_parameter('approach_forward_speed', 0.28)
        self.declare_parameter('avoid_turn_speed', 0.7)
        self.declare_parameter('vision_steering_gain', 1.5)
        self.declare_parameter('vision_timeout', 2.5)
        self.declare_parameter('scent_threshold_increase', 35.0)
        self.declare_parameter('scent_timeout', 6.0)
        self.declare_parameter('scent_turn_rate', 0.45)
        self.declare_parameter('explore_heading_interval', 8.0)
        self.declare_parameter('kp', 2.0)
        self.declare_parameter('ki', 0.0)
        self.declare_parameter('kd', 0.4)

        # State variables
        self.state = 'explore'
        self.previous_state = 'explore'
        self.current_heading = 0.0
        self.desired_heading = 0.0
        self.heading_error_integral = 0.0
        self.last_heading_error = 0.0
        self.last_heading_adjustment = self.get_clock().now()

        self.front_distance = None
        self.left_distance = None
        self.right_distance = None
        self.obstacle_direction = None
        self.last_obstacle_time = None

        self.scent_strength = None
        self.scent_baseline = None
        self.prev_scent_strength = None
        self.last_scent_time = None
        self.scent_history = deque(maxlen=30)
        self.scent_weave_direction = 1.0

        self.vision_detected = False
        self.vision_offset = 0.0
        self.last_vision_time = None

        self.last_ultrasonic_distance = None

        # Main control loop
        self.control_timer = self.create_timer(0.1, self.navigate)

    # --------------------------------------------------------------------- #
    # Sensor callbacks
    # --------------------------------------------------------------------- #
    def imu_callback(self, msg: Imu):
        self.current_heading = self.quaternion_to_yaw(msg.orientation)

    def scan_callback(self, msg: LaserScan):
        self.front_distance = self._sector_min(msg, -30, 30)
        self.left_distance = self._sector_min(msg, 30, 90)
        self.right_distance = self._sector_min(msg, -90, -30)

        front_threshold = self.get_parameter('obstacle_front_distance').value
        side_threshold = self.get_parameter('obstacle_side_distance').value

        if self.front_distance is not None and self.front_distance < front_threshold:
            self.previous_state = self.state
            # Pick the direction with more free space
            if (self.left_distance or math.inf) > (self.right_distance or math.inf):
                self.obstacle_direction = 'left'
            else:
                self.obstacle_direction = 'right'
            self.state = 'avoid_obstacle'
            self.last_obstacle_time = self.get_clock().now()
        elif self.state == 'avoid_obstacle':
            # Check if the path has cleared
            clear_time = self.get_parameter('obstacle_clear_time').value
            if self.front_distance is None or self.front_distance > front_threshold * 1.3:
                if self._elapsed(self.last_obstacle_time) > clear_time:
                    self.state = self._fallback_state()

        # Side proximity nudges the weave direction so the robot favours clear space
        if self.state != 'avoid_obstacle':
            if self.left_distance is not None and self.left_distance < side_threshold:
                self.scent_weave_direction = -1.0
            elif self.right_distance is not None and self.right_distance < side_threshold:
                self.scent_weave_direction = 1.0

    def gas_callback(self, msg: Int32MultiArray):
        if not msg.data:
            return

        mq2 = msg.data[0]
        ultrasonic = msg.data[3] if len(msg.data) > 3 else None
        now = self.get_clock().now()

        if self.scent_strength is None:
            self.scent_strength = float(mq2)
            self.scent_baseline = float(mq2)
        else:
            self.scent_strength = 0.7 * self.scent_strength + 0.3 * mq2
            self.scent_baseline = 0.995 * self.scent_baseline + 0.005 * self.scent_strength

        self.scent_history.append((self.time_seconds(now), self.scent_strength))
        self.last_scent_time = now

        if self.prev_scent_strength is not None:
            trend = self.scent_strength - self.prev_scent_strength
            if trend < -10.0:
                self.scent_weave_direction *= -1.0
        self.prev_scent_strength = self.scent_strength

        scent_delta = self.scent_strength - self.scent_baseline
        threshold = self.get_parameter('scent_threshold_increase').value
        if scent_delta > threshold:
            if self.state != 'approach_target':
                self.state = 'track_scent'

        self.last_ultrasonic_distance = ultrasonic if ultrasonic is not None and ultrasonic > 0 else None
        if self.last_ultrasonic_distance is not None and self.last_ultrasonic_distance < 25:
            self.previous_state = self.state
            self.state = 'avoid_obstacle'
            self.obstacle_direction = 'right'
            self.last_obstacle_time = now

    def vision_detected_callback(self, msg: Bool):
        now = self.get_clock().now()
        if msg.data:
            self.vision_detected = True
            self.last_vision_time = now
            self.state = 'approach_target'
        else:
            self.vision_detected = False

    def vision_offset_callback(self, msg: Float32):
        if self.vision_detected:
            self.vision_offset = float(msg.data)
            self.last_vision_time = self.get_clock().now()

    # --------------------------------------------------------------------- #
    # Control loop
    # --------------------------------------------------------------------- #
    def navigate(self):
        twist = Twist()
        now = self.get_clock().now()

        kp = self.get_parameter('kp').value
        ki = self.get_parameter('ki').value
        kd = self.get_parameter('kd').value

        # Decay scent state if no updates
        if self.state == 'track_scent' and not self._scent_active():
            self.state = 'explore'

        # Timeout vision lock if detection is stale
        if self.state == 'approach_target' and not self._vision_active():
            self.state = 'track_scent' if self._scent_active() else 'explore'
            self.vision_detected = False

        if self.state == 'avoid_obstacle':
            twist.linear.x = 0.0
            turn_speed = self.get_parameter('avoid_turn_speed').value
            twist.angular.z = turn_speed if self.obstacle_direction == 'left' else -turn_speed
        elif self.state == 'approach_target' and self.vision_detected:
            twist.linear.x = self.get_parameter('approach_forward_speed').value
            gain = self.get_parameter('vision_steering_gain').value
            twist.angular.z = wrap_angle(self.vision_offset) * gain
        elif self.state == 'track_scent' and self._scent_active():
            twist.linear.x = self.get_parameter('track_forward_speed').value
            turn_rate = self.get_parameter('scent_turn_rate').value
            # Shallow weave based on scent history
            twist.angular.z = self.scent_weave_direction * turn_rate
        else:
            self.state = 'explore'
            twist.linear.x = self.get_parameter('explore_forward_speed').value
            interval = self.get_parameter('explore_heading_interval').value
            if self._elapsed(self.last_heading_adjustment) > interval:
                delta = random.uniform(-math.radians(45), math.radians(45))
                self.desired_heading = wrap_angle(self.current_heading + delta)
                self.last_heading_adjustment = now

            heading_error = wrap_angle(self.desired_heading - self.current_heading)
            twist.angular.z = self.pid_control(heading_error, kp, ki, kd)

        self.cmd_vel_publisher.publish(twist)

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def pid_control(self, error, kp, ki, kd):
        dt = 0.1  # matches timer period
        self.heading_error_integral += error * dt
        self.heading_error_integral = max(-1.0, min(1.0, self.heading_error_integral))
        derivative = (error - self.last_heading_error) / dt

        output = kp * error + ki * self.heading_error_integral + kd * derivative
        self.last_heading_error = error
        return output

    def quaternion_to_yaw(self, orientation):
        x = orientation.x
        y = orientation.y
        z = orientation.z
        w = orientation.w
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        return math.atan2(siny_cosp, cosy_cosp)

    def _sector_min(self, scan, start_deg, end_deg):
        if not scan.ranges:
            return None
        angle_span = scan.angle_max - scan.angle_min
        if angle_span <= 0:
            return None
        total_samples = len(scan.ranges)
        start_index = int(((start_deg + 180.0) / 360.0) * total_samples)
        end_index = int(((end_deg + 180.0) / 360.0) * total_samples)
        if start_index > end_index:
            start_index, end_index = end_index, start_index
        start_index = max(0, min(total_samples - 1, start_index))
        end_index = max(0, min(total_samples, end_index))
        window = [
            r for r in scan.ranges[start_index:end_index]
            if scan.range_min <= r <= scan.range_max
        ]
        return min(window) if window else None

    def _elapsed(self, stamp):
        if stamp is None:
            return float('inf')
        return (self.get_clock().now() - stamp).nanoseconds / 1e9

    def _scent_active(self):
        if self.last_scent_time is None:
            return False
        timeout = self.get_parameter('scent_timeout').value
        return self._elapsed(self.last_scent_time) < timeout

    def _vision_active(self):
        if not self.vision_detected or self.last_vision_time is None:
            return False
        timeout = self.get_parameter('vision_timeout').value
        return self._elapsed(self.last_vision_time) < timeout

    def _fallback_state(self):
        if self._scent_active():
            return 'track_scent'
        if self._vision_active():
            return 'approach_target'
        return 'explore'

    @staticmethod
    def time_seconds(stamp):
        return stamp.nanoseconds / 1e9 if stamp is not None else 0.0


def main(args=None):
    rclpy.init(args=args)
    node = Navigator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Navigator interrupted by user.')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
