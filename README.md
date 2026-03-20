# Bio-Inspired Cross-Species Navigator

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![ROS: Noetic](https://img.shields.io/badge/ROS-Noetic-orange.svg)
![Platform: Intel Loihi 2](https://img.shields.io/badge/Platform-Intel%20Loihi%202-green.svg)
![Status: Submitted](https://img.shields.io/badge/Status-Submitted-yellow.svg)

This project implements a robotic navigation system inspired by the research paper "Evolutionary Convergence of Multimodal Navigation Algorithms in Mammals and Insects." The robot uses a combination of sensors to navigate its environment, mimicking the cross-species principles of path integration and goal-seeking behavior.

The system is built on a two-tiered architecture:
1.  **High-Level Control (Jetson Orin Nano)**: Runs ROS 2 for sensor processing (LiDAR, Camera, IMU), SLAM, and the primary navigation logic.
2.  **Low-Level Control (Arduino Nano)**: Manages real-time motor control and reads data from analog gas sensors (simulating olfactory cues).

---

### **System Architecture**
-   **Jetson Orin Nano**: Subscribes to sensor data, runs navigation algorithms, and publishes `Twist` velocity commands.
-   **Arduino Nano**: Subscribes to motor commands via serial and publishes sensor data back to the Jetson.

---

### **Hardware Requirements**
-   Jetson Orin Nano
-   Arduino Nano
-   2-motor robot chassis with a motor driver (e.g., L298N)
-   LiDAR (e.g., RPLIDAR)
-   IMU (e.g., MPU-6050)
-   RGB-D Camera (e.g., Intel RealSense)
-   Gas Sensors (MQ-2, MQ-135)

---

### **Setup and Installation**

1.  **Clone the Project:**
    ```bash
    git clone <your-repo-url> Bio-Inspired_Cross-Species_Navigator
    cd Bio-Inspired_Cross-Species_Navigator
    ```

2.  **Upload Arduino Code:**
    -   Open `arduino_controller/Robot_Controller/Robot_Controller.ino` in the Arduino IDE.
    -   Select your board (Arduino Nano) and port.
    -   Click "Upload".

3.  **Pull external drivers:**
    ```bash
    cd ros2_ws/src
    git clone https://github.com/Slamtec/rplidar_ros.git            # LiDAR driver
    git clone https://github.com/LP-Research/lpms_ig1.git            # IMU driver (optional)
    cd ..
    ```

4.  **Install software dependencies (on the Jetson):**
    ```bash
    sudo apt-get update
    sudo apt-get install ros-humble-cv-bridge ros-humble-vision-msgs
    pip install pyserial opencv-python numpy
    ```

5.  **Build the ROS 2 workspace:**
    ```bash
    cd ~/Bio-Inspired_Cross-Species_Navigator/ros2_ws
    colcon build --symlink-install
    source install/setup.bash
    ```
---

### **Running the Project**

1.  **Source the Workspace:**
    Open a new terminal and run:
    ```bash
    source ~/Bio-Inspired_Cross-Species_Navigator/ros2_ws/install/setup.bash
    ```

2.  **Launch hardware drivers (each in its own terminal):**
    ```bash
    # LiDAR (adjust port if you created a udev symlink)
    ros2 launch rplidar_ros rplidar.launch.py serial_port:=/dev/ttyUSB0

    # IMU (only if lpms_ig1 is installed and the device is connected)
    ros2 launch lpms_ig1 bringup.launch.py port:=/dev/ttyUSB1
    ```

3.  **Start the full navigation stack:**
    ```bash
    ros2 launch robot_navigation start_navigation.launch.py
    ```
    The launch file starts the camera publisher, colour-based `vision_processor`, base controller, and the multisensor `navigator`. Override parameters on the command line if the defaults do not match your hardware (e.g. `arduino_port`, `target_hue`, or obstacle distances).

4.  **Observe the behaviour:**
    - `ros2 topic echo /gas_sensors` – view MQ-2/MQ-135/CO₂/ultrasonic readings.
    - `ros2 topic echo /cmd_vel` – verify autonomous velocity commands.
    - `rviz2 -d rviz_config.rviz` – visualise `/scan` data and the vision debug feed (enable `vision/debug_image`).

---

### **Dog-Inspired Autonomy**

The navigator blends all sensors into four high-level behaviours:

- **Explore** – default mode, keeps a nominal heading while periodically drifting like a searching dog.
- **Track Scent** – triggered when gas concentration rises above baseline. The robot slows down and performs a shallow weave to remain inside the plume.
- **Approach Target** – activated when the vision processor recognises the configured colour signature. The robot aligns to the camera bearing while advancing.
- **Avoid Obstacle** – supersedes other states whenever the LiDAR or ultrasonic data indicate danger, backing away and turning towards free space.

Tune the behaviour via ROS parameters (see `launch/start_navigation.launch.py`) or dynamically with `ros2 param set`. Adjust `target_hue`/`target_hue_tolerance` to match the colour of the object you want the robot to “seek” once it catches the scent. 

---

### **Autonomous Navigation Stack (SLAM + Nav2 + GPS fusion)**

For full-field missions that blend SLAM, GPS, and multi-sensor decision making, use the new launch file:

```bash
cd ~/Bio-Inspired_Cross-Species_Navigator/ros2_ws
source install/setup.bash
ros2 launch robot_navigation autonomous_navigation.launch.py \
    waypoints_yaml:="[{'name': 'start', 'x': 0.0, 'y': 0.0, 'yaw': 0.0}]"
```

This brings up:
- `slam_toolbox` (if `enable_slam:=true`) with parameters in `config/slam_toolbox.yaml`
- `robot_localization` EKF and navsat transform using `config/localization.yaml`
- Nav2 bringup with `config/nav2_params.yaml`
- Existing camera/vision/base controller nodes
- A new `mission_manager` node that dispatches Nav2 goals from the `waypoints_yaml` parameter, pauses when gas or vision triggers fire, and can loop through waypoints.

**To complete the hardware integration:**
1. Ensure LiDAR publishes on `/scan`, IMU on `/imu/data`, GPS on `/gps/fix`, wheel odometry on `/wheel/odometry`, and any additional obstacle sensors are fed into Nav2 costmaps.
2. Calibrate `config/localization.yaml` with your real sensor noise characteristics and topic names.
3. Populate the waypoint list with map-frame targets (or extend `mission_manager` to convert GPS coordinates to map positions).
4. Launch NavSat + GPS drivers before `autonomous_navigation.launch.py`, or set `use_gps_gate:=false` if GPS is optional.
5. Use `ros2 param set /mission_manager waypoints_yaml "..."` at runtime to modify missions without relaunching.

The default configuration assumes a 2D planar robot, differential drive kinematics, and a SLAM Toolbox map running in the `map` frame. Adjust costmap sizes, inflation radii, and controller constraints in `config/nav2_params.yaml` to match the robot’s footprint and speed limits. 

cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws && source devel/setup.bash && roslaunch bio_inspired_nav simple_simulation.launch

# Check the log file
cat /tmp/bio_nav_logs/nav_log_20260101_121123.csv

# Monitor in real-time
tail -f /tmp/bio_nav_logs/nav_log_*.csv

cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
source devel/setup.bash
export DISPLAY=:0
roslaunch bio_inspired_nav rviz_visualization.launch


# Terminal 1: Start Long-Running Training
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
./start_training.sh 500 50 300

# Terminal 2: Monitor Progress
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
rosrun bio_inspired_nav monitor_training.py

# Terminal 3: Check Status & Results
# Check current episode progress
cat /tmp/bio_nav_training_results/progress.json

# Check latest results
tail -10 /tmp/bio_nav_training_results/training_results_*.csv

# Check log files
ls -la /tmp/bio_nav_logs/

# Terminal 1
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
export DISPLAY=:0
roslaunch bio_inspired_nav simple_simulation.launch


# Terminal 2
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash
export DISPLAY=:0
rviz -d src/bio_inspired_nav/rviz/bio_nav.rviz