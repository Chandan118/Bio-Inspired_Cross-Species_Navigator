# (Content is the same as provided in the previous answer, with minor name change)
#!/usr/bin/env python3
import glob
import time

import rclpy
import serial
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from std_msgs.msg import Int32MultiArray


class MockSerial:
    """Very small mock that mimics the subset of pyserial needed by this node."""

    def __init__(self, logger):
        self._logger = logger
        self._buffer = []

    def write(self, data):
        # Log the outgoing command to aid debugging when no hardware is connected.
        self._logger.debug(f"[MockSerial] Command: {data.decode(errors='ignore').strip()}")

    def flush(self):
        pass

    @property
    def in_waiting(self):
        return len(self._buffer)

    def readline(self):
        if self._buffer:
            return self._buffer.pop(0)
        return b""

    def reset_input_buffer(self):
        self._buffer.clear()

    def feed_sensor_sample(self, mq2_value, mq135_value):
        payload = f"s,{mq2_value},{mq135_value}\n".encode("utf-8")
        self._buffer.append(payload)

class BaseController(Node):
    def __init__(self):
        super().__init__('base_controller')
        self.get_logger().info('Base Controller Node Started')
        
        # Declare parameters first
        self.declare_parameter(
            'arduino_port',
            '/dev/ttyACM0',
            ParameterDescriptor(description='Preferred serial port for the Arduino controller'),
        )
        self.declare_parameter(
            'fallback_ports',
            [
                '/dev/ttyUSB0',
                '/dev/ttyUSB1',
                '/dev/ttyACM0',
                '/dev/ttyACM1',
            ],
            ParameterDescriptor(
                description='Additional serial port patterns to try when connecting',
            ),
        )
        self.declare_parameter(
            'mock_serial_on_error',
            True,
            ParameterDescriptor(
                description=(
                    'Switch to an in-process mock serial interface if the Arduino is unavailable.'
                ),
            ),
        )
        self.declare_parameter(
            'baud_rate',
            9600,
            ParameterDescriptor(description='Serial baud rate for the Arduino connection'),
        )
        self.declare_parameter(
            'sensor_poll_interval',
            1.0,
            ParameterDescriptor(description='Interval in seconds between automatic sensor polls'),
        )
        self.declare_parameter(
            'sensor_command_sequence',
            ['M', 'C', 'O', 'U'],
            ParameterDescriptor(description='Commands to request sensor readings from the Arduino'),
        )
        self.declare_parameter(
            'sensor_read_wait',
            0.2,
            ParameterDescriptor(description='Time (s) to wait after sending a sensor command before reading'),
        )
        self.declare_parameter(
            'motor_command_mode',
            'simple',
            ParameterDescriptor(
                description="Motor command protocol: 'simple' sends single-character commands, 'differential' sends PWM pairs."
            ),
        )
        self.declare_parameter(
            'simple_linear_threshold',
            0.05,
            ParameterDescriptor(description='Minimum |linear.x| to trigger forward/backward commands in simple mode'),
        )
        self.declare_parameter(
            'simple_angular_threshold',
            0.1,
            ParameterDescriptor(description='Minimum |angular.z| to trigger turn commands in simple mode'),
        )
        self.declare_parameter('wheel_base', 0.5)
        self.declare_parameter('wheel_radius', 0.1)

        self.mock_mode = False
        self._mock_sensor_timer = None
        self._last_sensor_rx = None
        self._last_sensor_warn = 0.0
        self._sensor_poll_timer = None
        self._sensor_poll_index = 0
        self.sensor_names = ['mq2', 'mq135', 'co2', 'ultrasonic']
        self.last_sensor_values = {name: 0 for name in self.sensor_names}
        self.sensor_command_sequence = []
        self._sensor_values_initialised = False
        mode_param = self.get_parameter('motor_command_mode').get_parameter_value().string_value
        self.motor_command_mode = (mode_param or 'simple').lower()
        self.simple_linear_threshold = (
            self.get_parameter('simple_linear_threshold').get_parameter_value().double_value
        )
        self.simple_angular_threshold = (
            self.get_parameter('simple_angular_threshold').get_parameter_value().double_value
        )
        self._last_simple_command = None

        self.arduino = self._initialise_serial()

        # Publisher for sensor data
        self.sensor_publisher = self.create_publisher(Int32MultiArray, 'gas_sensors', 10)

        # Subscriber for motor commands (from the navigator)
        self.cmd_vel_subscriber = self.create_subscription(
            Twist,
            'cmd_vel',
            self.cmd_vel_callback,
            10)

        # Timer for reading from Arduino
        self.timer = self.create_timer(0.1, self.read_from_arduino)
        if self.mock_mode:
            # In mock mode we synthesize sensor samples so downstream nodes can continue to operate.
            self._mock_sensor_timer = self.create_timer(0.5, self._publish_mock_sensor_sample)
        else:
            sensor_commands_param = self.get_parameter('sensor_command_sequence').get_parameter_value()
            sensor_commands = list(sensor_commands_param.string_array_value)
            poll_interval = self.get_parameter('sensor_poll_interval').get_parameter_value().double_value
            if sensor_commands and poll_interval > 0.0:
                self.sensor_command_sequence = sensor_commands
                self._sensor_poll_timer = self.create_timer(poll_interval, self._poll_sensors)
            else:
                self.sensor_command_sequence = []


    def cmd_vel_callback(self, msg):
        # Convert Twist message to motor speeds
        linear_x = msg.linear.x
        angular_z = msg.angular.z

        if self.motor_command_mode == 'differential':
            self._last_simple_command = None
            # Simple differential drive kinematics
            # You will need to tune these values for your robot's specific geometry
            wheel_base = self.get_parameter('wheel_base').get_parameter_value().double_value
            wheel_radius = self.get_parameter('wheel_radius').get_parameter_value().double_value

            right_speed = (linear_x / wheel_radius) + (angular_z * wheel_base / (2 * wheel_radius))
            left_speed = (linear_x / wheel_radius) - (angular_z * wheel_base / (2 * wheel_radius))

            # Convert to PWM values (0-255)
            # This is a simple mapping and might need refinement
            left_pwm = int(left_speed * 100)
            right_pwm = int(right_speed * 100)
            
            # Send to Arduino
            command = f"m,{left_pwm},{right_pwm}\n"
            self.arduino.write(command.encode())
        else:
            command_char = self._select_simple_motor_command(linear_x, angular_z)
            if command_char and command_char != self._last_simple_command:
                try:
                    self.arduino.write(command_char.encode('utf-8'))
                    if hasattr(self.arduino, 'flush'):
                        try:
                            self.arduino.flush()
                        except Exception:
                            pass
                except Exception as exc:
                    self.get_logger().warning(f'Failed to send motor command "{command_char}": {exc}')
                else:
                    self._last_simple_command = command_char

    def read_from_arduino(self):
        wait_time = self.get_parameter('sensor_read_wait').value
        if wait_time > 0:
            time.sleep(wait_time)
        while True:
            try:
                raw_line = self.arduino.readline()
            except Exception as exc:
                self.get_logger().warning(f'Error reading from Arduino: {exc}')
                return

            if not raw_line:
                break

            line = raw_line.decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            if not line.startswith('s,'):
                if self._process_textual_sensor_line(line):
                    continue
                # Allow the Arduino to log other diagnostic lines without spamming INFO.
                self.get_logger().debug(f'Ignoring non-sensor line from Arduino: {line}')
                continue

            tokens = line.split(',')[1:]
            sensor_values = []
            for token in tokens:
                token = token.strip()
                if not token:
                    continue
                if '=' in token:
                    _, token = token.split('=', 1)
                    token = token.strip()
                try:
                    sensor_values.append(int(float(token)))
                except ValueError:
                    self.get_logger().warning(f'Unable to parse sensor value "{token}" from line: {line}')
                    sensor_values = []
                    break

            if not sensor_values:
                self.get_logger().debug(f'No sensor values extracted from line: {line}')
                continue

            self._update_sensor_values(sensor_values)

        now = time.time()
        if (
            (self._last_sensor_rx is None or (now - self._last_sensor_rx) > 5.0)
            and (now - self._last_sensor_warn) > 5.0
        ):
            self.get_logger().warning('No sensor data received from Arduino in the last 5 seconds.')
            self._last_sensor_warn = now

    def _initialise_serial(self):
        port_param = self.get_parameter('arduino_port').get_parameter_value().string_value.strip()
        fallback_patterns = self.get_parameter('fallback_ports').get_parameter_value().string_array_value
        allow_mock = self.get_parameter('mock_serial_on_error').get_parameter_value().bool_value

        candidate_ports = []
        if port_param:
            matches = glob.glob(port_param)
            candidate_ports.extend(matches if matches else [port_param])

        for pattern in fallback_patterns:
            matches = glob.glob(pattern)
            if matches:
                candidate_ports.extend(matches)
            else:
                candidate_ports.append(pattern)

        # Deduplicate while preserving order
        seen = set()
        ordered_candidates = []
        for port in candidate_ports:
            if port not in seen:
                seen.add(port)
                ordered_candidates.append(port)

        if not ordered_candidates:
            ordered_candidates.append('/dev/ttyACM0')

        for candidate in ordered_candidates:
            try:
                self.get_logger().info(f'Trying Arduino connection on {candidate}')
                baud_rate = self.get_parameter('baud_rate').get_parameter_value().integer_value
                serial_port = serial.Serial(candidate, baud_rate, timeout=1)
                time.sleep(2)  # Give Arduino time to initialise
                try:
                    serial_port.reset_input_buffer()
                except AttributeError:
                    pass
                self.get_logger().info(f'Arduino connected on {candidate}')
                return serial_port
            except Exception as exc:
                self.get_logger().warning(f'Unable to open {candidate}: {exc}')

        if allow_mock:
            self.get_logger().warning(
                'Arduino connection failed; switching to in-process mock serial interface. '
                'Set mock_serial_on_error=false to require a real device.'
            )
            self.mock_mode = True
            return MockSerial(self.get_logger())

        self.get_logger().fatal('Failed to connect to Arduino after trying all configured ports.')
        raise RuntimeError('Failed to connect to Arduino')

    def _publish_mock_sensor_sample(self):
        if isinstance(self.arduino, MockSerial):
            # Provide representative but deterministic values so downstream processing can run.
            self.arduino.feed_sensor_sample(300, 250)
            self.arduino.feed_sensor_sample(320, 260)
            self.arduino.feed_sensor_sample(310, 255)
            self._update_sensor_values([300, 250, 400, 60])

    def _poll_sensors(self):
        if not self.sensor_command_sequence:
            return
        if not hasattr(self.arduino, 'write'):
            return
        try:
            command = self.sensor_command_sequence[self._sensor_poll_index]
        except IndexError:
            return
        self._sensor_poll_index = (self._sensor_poll_index + 1) % len(self.sensor_command_sequence)
        try:
            self.arduino.write(command.encode('utf-8'))
            if hasattr(self.arduino, 'flush'):
                try:
                    self.arduino.flush()
                except Exception:
                    pass
            self.get_logger().debug(f'Sent sensor command "{command}"')
        except Exception as exc:
            self.get_logger().warning(f'Failed to send sensor command "{command}": {exc}')

    def _update_sensor_values(self, sensor_values):
        updates = {}
        for idx, value in enumerate(sensor_values):
            if idx < len(self.sensor_names):
                updates[self.sensor_names[idx]] = value
        if updates:
            self._apply_sensor_updates(updates)

    def _process_textual_sensor_line(self, line):
        """Parse human-readable sensor output from the Arduino."""
        lowered = line.lower()
        updates = {}

        def extract_int(text):
            number = ''
            negative = False
            for char in text:
                if char.isdigit():
                    number += char
                elif char == '-' and not number:
                    negative = True
                elif number:
                    break
            if not number:
                return None
            value = int(number)
            return -value if negative else value

        mapping = {
            'mq2': ['mq-2', 'mq2'],
            'mq135': ['mq-135', 'mq135'],
            'co2': ['co2'],
            'ultrasonic': ['ultrasonic', 'distance'],
        }

        for sensor_name, keywords in mapping.items():
            if any(keyword in lowered for keyword in keywords):
                value = extract_int(line)
                if value is not None:
                    updates[sensor_name] = value

        if updates:
            self._apply_sensor_updates(updates)
            return True
        return False

    def _apply_sensor_updates(self, updates):
        any_value = False
        changed = False
        for name, value in updates.items():
            if name not in self.last_sensor_values:
                continue
            any_value = True
            if self.last_sensor_values[name] != value:
                self.last_sensor_values[name] = value
                changed = True
        if any_value and (changed or not self._sensor_values_initialised):
            sensor_msg = Int32MultiArray()
            sensor_msg.data = [self.last_sensor_values[name] for name in self.sensor_names]
            self.sensor_publisher.publish(sensor_msg)
            self._last_sensor_rx = time.time()
            self._last_sensor_warn = 0.0
            self._sensor_values_initialised = True
        return any_value

    def _select_simple_motor_command(self, linear_x, angular_z):
        if abs(linear_x) >= self.simple_linear_threshold:
            return 'F' if linear_x > 0 else 'B'
        if abs(angular_z) >= self.simple_angular_threshold:
            return 'L' if angular_z > 0 else 'R'
        return 'S'
                        
def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = BaseController()
        rclpy.spin(node)
    except (RuntimeError, KeyboardInterrupt):
        pass
    finally:
        if node:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()
