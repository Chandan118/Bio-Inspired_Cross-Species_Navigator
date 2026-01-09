#!/usr/bin/env python3
import math
import threading
from typing import List, Optional

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Bool, Int32MultiArray


def yaw_to_quaternion(yaw: float) -> Quaternion:
    quat = Quaternion()
    quat.z = math.sin(yaw / 2.0)
    quat.w = math.cos(yaw / 2.0)
    return quat


class MissionManager(Node):
    """
    High-level coordinator that blends GPS waypoints, scent events, and vision cues.

    The node drives Nav2 by dispatching NavigateToPose goals. Parameters:
      - waypoints_yaml: YAML string defining waypoints [{name, x, y, yaw}]
      - loop_waypoints: whether to cycle through the list
      - gas_threshold: MQ-2 reading that triggers hold_for_scent behaviour
      - hold_duration: seconds to pause after a scent or vision event
      - use_gps_gate: if true, waits for a valid NavSatFix before sending first goal
    """

    def __init__(self):
        super().__init__('mission_manager')

        self.declare_parameter('waypoints_yaml', '[]')
        self.declare_parameter('loop_waypoints', True)
        self.declare_parameter('gas_threshold', 400.0)
        self.declare_parameter('hold_duration', 5.0)
        self.declare_parameter('use_gps_gate', False)

        self._load_waypoints()

        self._loop_waypoints = self.get_parameter('loop_waypoints').get_parameter_value().bool_value
        self._gas_threshold = self.get_parameter('gas_threshold').get_parameter_value().double_value
        self._hold_duration = self.get_parameter('hold_duration').get_parameter_value().double_value
        self._use_gps_gate = self.get_parameter('use_gps_gate').get_parameter_value().bool_value

        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._current_goal_handle = None
        self._current_goal_future = None
        self._current_index = 0
        self._hold_until = self.get_clock().now()
        self._gps_ready = not self._use_gps_gate

        self._waypoint_lock = threading.Lock()

        # Subscriptions
        self.create_subscription(Int32MultiArray, 'gas_sensors', self._gas_callback, 10)
        self.create_subscription(Bool, 'vision/target_detected', self._vision_callback, 10)
        self.create_subscription(NavSatFix, 'gps/fix', self._gps_callback, 10)

        # Main executor timer
        self.create_timer(1.0, self._mission_tick)

        self.get_logger().info('Mission manager ready with %d waypoint(s).', len(self._waypoints))

    # --------------------------------------------------------------------- #
    # Parameter helpers
    # --------------------------------------------------------------------- #
    def _load_waypoints(self):
        import yaml

        raw = self.get_parameter('waypoints_yaml').get_parameter_value().string_value
        waypoints: List[dict] = []
        try:
            parsed = yaml.safe_load(raw) if raw else []
            if isinstance(parsed, list):
                waypoints = parsed
        except yaml.YAMLError as exc:
            self.get_logger().error(f'Failed to parse waypoints_yaml: {exc}')

        self._waypoints: List[dict] = waypoints

    # --------------------------------------------------------------------- #
    # Sensor callbacks
    # --------------------------------------------------------------------- #
    def _gas_callback(self, msg: Int32MultiArray):
        if not msg.data:
            return
        mq2_val = msg.data[0]
        if mq2_val >= self._gas_threshold:
            self.get_logger().info('Gas threshold exceeded (MQ-2=%d); holding position for %.1fs.', mq2_val, self._hold_duration)
            self._hold_until = self.get_clock().now() + Duration(seconds=self._hold_duration)
            self._cancel_goal(reason='gas plume detected')

    def _vision_callback(self, msg: Bool):
        if msg.data:
            self.get_logger().info('Target detected by vision; pausing mission for %.1fs.', self._hold_duration)
            self._hold_until = self.get_clock().now() + Duration(seconds=self._hold_duration)
            self._cancel_goal(reason='vision target detected')

    def _gps_callback(self, msg: NavSatFix):
        if msg.status.status >= 0 and self._use_gps_gate and not self._gps_ready:
            self.get_logger().info('GPS fix acquired; mission unlocked.')
            self._gps_ready = True

    # --------------------------------------------------------------------- #
    # Mission loop / Nav2 integration
    # --------------------------------------------------------------------- #
    def _mission_tick(self):
        if not self._gps_ready:
            self.get_logger().debug('Waiting for GPS fix before starting mission.')
            return

        if not self._nav_client.wait_for_server(timeout_sec=0.1):
            self.get_logger().warn_once('Waiting for Nav2 navigate_to_pose action server...')
            return

        if self.get_clock().now() < self._hold_until:
            return

        if self._current_goal_future is not None and not self._current_goal_future.done():
            return

        if self._current_goal_future is not None and self._current_goal_future.done():
            result_future = self._current_goal_future.result()
            status = getattr(result_future, 'status', GoalStatus.STATUS_UNKNOWN)
            if status != GoalStatus.STATUS_SUCCEEDED:
                self.get_logger().warn('Previous goal finished with status %d', status)
            else:
                self.get_logger().info('Previous goal succeeded.')
            self._current_goal_handle = None
            self._current_goal_future = None

        waypoint = self._next_waypoint()
        if waypoint is None:
            self.get_logger().info('Mission complete; no more waypoints to dispatch.')
            return

        goal_msg = self._waypoint_to_goal(waypoint)
        self.get_logger().info('Dispatching Nav2 goal: %s (x=%.2f, y=%.2f, yaw=%.2f)',
                               waypoint.get('name', 'unnamed'),
                               waypoint['x'], waypoint['y'], waypoint['yaw'])
        send_future = self._nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self._nav_feedback_cb,
        )
        send_future.add_done_callback(self._nav_goal_response_cb)

    def _next_waypoint(self) -> Optional[dict]:
        with self._waypoint_lock:
            if not self._waypoints:
                return None
            if self._current_index >= len(self._waypoints):
                if not self._loop_waypoints:
                    return None
                self._current_index = 0
            waypoint = self._waypoints[self._current_index]
            self._current_index += 1
            return waypoint

    def _waypoint_to_goal(self, waypoint: dict) -> NavigateToPose.Goal:
        goal = NavigateToPose.Goal()
        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(waypoint.get('x', 0.0))
        pose.pose.position.y = float(waypoint.get('y', 0.0))
        yaw = float(waypoint.get('yaw', 0.0))
        pose.pose.orientation = yaw_to_quaternion(yaw)
        goal.pose = pose
        return goal

    # ------------------------------------------------------------------ #
    # Nav2 callbacks
    # ------------------------------------------------------------------ #
    def _nav_goal_response_cb(self, future):
        goal_handle = future.result()
        if not goal_handle.accepted:
            self.get_logger().warn('Nav2 goal was rejected.')
            self._current_goal_handle = None
            self._current_goal_future = None
            return
        self.get_logger().info('Nav2 goal accepted.')
        self._current_goal_handle = goal_handle
        self._current_goal_future = goal_handle.get_result_async()

    def _nav_feedback_cb(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().debug('Remaining distance: %.2f', feedback.distance_remaining)

    def _cancel_goal(self, reason: str):
        if self._current_goal_handle and self._current_goal_handle.is_active:
            self.get_logger().info('Cancelling Nav2 goal due to %s.', reason)
            cancel_future = self._current_goal_handle.cancel_goal_async()
            cancel_future.add_done_callback(lambda _: self.get_logger().debug('Goal cancel request sent.'))
            self._current_goal_future = None
            self._current_goal_handle = None


def main(args=None):
    rclpy.init(args=args)
    node = MissionManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Mission manager interrupted by user.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
