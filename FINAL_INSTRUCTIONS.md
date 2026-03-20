# ✅ Bio-Inspired Cross-Species Navigator – Field Run Checklist

The stack now mirrors the behaviour of a scent-tracking dog. Follow this sequence whenever you deploy on the Jetson:

1. **Hardware bring-up**
   ```bash
   # LiDAR (adjust the port or udev symlink that you created)
   ros2 launch rplidar_ros rplidar.launch.py serial_port:=/dev/ttyUSB0

   # IMU (optional)
   ros2 launch lpms_ig1 bringup.launch.py port:=/dev/ttyUSB1
   ```

2. **Launch the autonomous navigation suite**
   ```bash
   cd ~/Bio-Inspired_Cross-Species_Navigator/ros2_ws
   source install/setup.bash
   ros2 launch robot_navigation start_navigation.launch.py
   ```
   This starts:
   - `camera_publisher` (Jetson GStreamer pipeline)
   - `vision_processor` (colour target tracking → `vision/target_*`)
   - `base_controller` (Arduino bridge at 9600 baud using `F/B/L/R/S` commands)
   - `navigator` (multimodal state machine: explore → track scent → approach target → avoid obstacle)

3. **Monitor live topics (new terminal, same setup)**
   ```bash
   ros2 topic echo /gas_sensors
   ros2 topic echo /cmd_vel
   ros2 topic echo /scan
   ```
   Launch RViz with `rviz2 -d ../rviz_config.rviz` to see lidar returns and optionally enable `vision/debug_image`.

4. **Tuning tips**
   - Colour tracking: adjust `target_hue` / `target_hue_tolerance` on the `vision_processor`.
   - Scent response: tweak `scent_threshold_increase`, `scent_turn_rate`, and `scent_timeout`.
   - Obstacle thresholds: modify `obstacle_front_distance` / `obstacle_side_distance` for your chassis width.

5. **Shutdown**
   Stop the navigation launch with `Ctrl+C`, then halt the lidar/imu drivers. Always power down the Arduino last to avoid dangling serial ports.

With all sensors active, the robot will explore, lock onto gas plumes, visually confirm the target colour, and reroute around obstacles autonomously. Adjust parameters at runtime using `ros2 param set <node> <name> <value>` to fine-tune behaviour in the field. 

---

### Full Autonomy (Nav2 + SLAM + GPS)

When you are ready to run with SLAM, Nav2, and GPS fusion:

1. Start sensor drivers: LiDAR → `/scan`, IMU → `/imu/data`, GPS → `/gps/fix`, wheel odometry → `/wheel/odometry`.
2. Launch the expanded stack:
   ```bash
   cd ~/Bio-Inspired_Cross-Species_Navigator/ros2_ws
   source install/setup.bash
   ros2 launch robot_navigation autonomous_navigation.launch.py \
       waypoints_yaml:="[{'name': 'wp1', 'x': 1.0, 'y': 0.0, 'yaw': 0.0}]"
   ```
   - `slam_toolbox` builds or refines the map (disable with `enable_slam:=false` if you have a static map).
   - `robot_localization` fuses odometry, IMU, and GPS (edit `config/localization.yaml` to match your topics).
   - Nav2 handles planning and recovery using `config/nav2_params.yaml`.
   - `mission_manager` dispatches waypoints and pauses when gas or vision triggers fire.
3. Update missions on the fly:
   ```bash
   ros2 param set /mission_manager waypoints_yaml "[{'name': 'site_a', 'x': 4.0, 'y': 2.5, 'yaw': 1.57}]"
   ```
4. Use RViz to visualise `/map`, `/scan`, costmaps, and Nav2 goals. Record bags for tuning.

Tune costmaps, controller limits, and waypoint lists to match your chassis. Add waypoint conversion logic if you plan to feed raw GPS coordinates (currently the mission manager expects map-frame poses). 
