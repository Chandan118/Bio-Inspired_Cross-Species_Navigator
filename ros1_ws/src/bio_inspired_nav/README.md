# Bio-Inspired Cross-Species Navigator - ROS 1 Simulation

A comprehensive ROS 1 simulation implementing bio-inspired navigation algorithms with machine learning. This project combines multi-sensor fusion, reinforcement learning, and biomimetic strategies from insects and mammals for autonomous navigation.

## 🌟 Features

### Machine Learning Integration
- **Deep Q-Network (DQN)** for navigation decision-making with TensorFlow
- **Q-Learning** fallback when TensorFlow not available
- **CNN-based Vision Processing** using MobileNetV2 for object detection
- **Gradient-based Gas Plume Tracking** mimicking insect chemotaxis

### Sensor Fusion
- LiDAR (360° scanning)
- RGB Camera with CNN/color-based target detection
- IMU for orientation tracking
- Gas sensors (simulated) with gradient estimation
- Odometry for position tracking

### Bio-Inspired Behaviors
1. **Lévy Flight Search** - Random exploration with occasional long jumps
2. **Moth-Inspired Chemotaxis** - Surge, cast, and track behaviors
3. **Gradient Following** - Adaptive learning for optimal approach
4. **Multi-modal State Machine** - Exploration, tracking, approaching, avoiding

## 📋 Prerequisites

### Required
```bash
# ROS Noetic (Ubuntu 20.04) or ROS Melodic (Ubuntu 18.04)
# Gazebo 11
# Python 2.7 or 3.x

sudo apt-get update
sudo apt-get install -y \
    ros-noetic-desktop-full \
    ros-noetic-gazebo-ros-pkgs \
    ros-noetic-gazebo-ros-control \
    ros-noetic-joint-state-publisher \
    ros-noetic-robot-state-publisher \
    ros-noetic-xacro \
    python3-pip \
    python3-numpy \
    python3-matplotlib \
    python3-opencv
```

### Optional (for ML features)
```bash
# TensorFlow for DQN
pip3 install tensorflow==2.8.0

# Additional ML libraries
pip3 install keras scikit-learn
```

## 🚀 Installation

### 1. Clone and Build
```bash
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
catkin_make
source devel/setup.bash
```

### 2. Make Scripts Executable
```bash
cd src/bio_inspired_nav/scripts
chmod +x *.py
```

### 3. Verify Installation
```bash
rospack find bio_inspired_nav
```

## 🎮 Running the Simulation

### Quick Start (Training Mode)
```bash
# Terminal 1: Start complete simulation
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
source devel/setup.bash
roslaunch bio_inspired_nav complete_simulation.launch
```

### Advanced Usage

#### Training with Machine Learning
```bash
# Run training for 50 episodes with visualization
roslaunch bio_inspired_nav complete_simulation.launch \
    use_ml:=true \
    training_mode:=true \
    gui:=true
```

#### Evaluation Mode (No Learning)
```bash
roslaunch bio_inspired_nav complete_simulation.launch \
    use_ml:=true \
    training_mode:=false
```

#### Headless Mode (Faster Training)
```bash
roslaunch bio_inspired_nav complete_simulation.launch \
    gui:=false \
    headless:=true \
    training_mode:=true
```

#### Run Automated Training Script
```bash
# Training mode
python3 src/bio_inspired_nav/scripts/run_simulation.py \
    --training \
    --episodes 100 \
    --use-ml \
    --gui

# Evaluation mode
python3 src/bio_inspired_nav/scripts/run_simulation.py \
    --evaluation \
    --eval-episodes 20 \
    --use-ml
```

## 📊 Monitoring and Visualization

### RViz Visualization
The simulation automatically launches RViz with pre-configured views:
- Robot model
- LiDAR scan
- Camera feed with debug overlay
- Odometry trail
- Transform tree

### Real-time Data Logging
Data is automatically logged to `/tmp/bio_nav_logs/` including:
- Trajectory data (x, y, yaw)
- Sensor readings (gas, lidar, vision)
- Velocity commands
- Navigation states
- Performance metrics

### Live Plots
Enable real-time plotting:
```bash
rosrun bio_inspired_nav data_logger.py _enable_plotting:=true
```

## 🔧 Configuration

### Adjust Gas Source Location
Edit `launch/complete_simulation.launch`:
```xml
<param name="source_x" value="8.0"/>  <!-- Change X coordinate -->
<param name="source_y" value="8.0"/>  <!-- Change Y coordinate -->
```

### Tune Navigation Parameters
Modify parameters in `scripts/bio_navigator_rl.py`:
- Learning rate
- Exploration rate (epsilon)
- Reward structure
- Action space

### Change Robot Starting Position
```bash
roslaunch bio_inspired_nav complete_simulation.launch \
    x_pos:=2.0 \
    y_pos:=3.0 \
    yaw:=1.57
```

## 📈 Results and Metrics

### Performance Metrics
- **Success Rate**: Percentage of runs reaching target
- **Time to Target**: Average time to locate gas source
- **Path Efficiency**: Ratio of direct path to actual path
- **Collision Rate**: Frequency of obstacle collisions
- **Coverage**: Area explored during search

### Accessing Results
```bash
# View logs
cd /tmp/bio_nav_logs/
ls -lh

# View plots
eog nav_log_YYYYMMDD_HHMMSS_plots.png
```

## 🧪 Experiment Scenarios

### Scenario 1: Simple Navigation
- Goal: Find orange target in open environment
- Sensors: LiDAR + Vision
- Success metric: Distance < 0.5m

### Scenario 2: Gas Plume Tracking
- Goal: Locate gas source following concentration gradient
- Sensors: Gas sensors + LiDAR
- Success metric: Concentration > 90% of source strength

### Scenario 3: Multi-modal Navigation
- Goal: Use all sensors to navigate complex environment
- Sensors: All (LiDAR, Camera, IMU, Gas)
- Success metric: Reach target with minimal collisions

## 🎯 Key Nodes

### 1. bio_navigator_rl
Main navigation controller with RL
- Input: All sensor data
- Output: `/cmd_vel` (velocity commands)
- Model: DQN or Q-Learning

### 2. vision_processor_cnn
Object detection and tracking
- Input: `/camera/rgb/image_raw`
- Output: `/vision/target_detected`, `/vision/target_offset`
- Model: MobileNetV2 or color-based

### 3. gas_plume_tracker
Chemotaxis-based gas tracking
- Input: `/gas_sensors`, `/odom`
- Output: `/gas_plume/cmd_vel`, `/gas_plume/gradient`
- Algorithm: Gradient ascent with casting

### 4. gas_sensor_simulator
Simulates realistic gas dispersion
- Input: `/odom`
- Output: `/gas_sensors`
- Model: Gaussian plume with wind effects

### 5. data_logger
Comprehensive data recording
- Input: All topics
- Output: CSV files, plots
- Features: Real-time visualization

## 🐛 Troubleshooting

### Gazebo won't start
```bash
killall gzserver gzclient
roslaunch bio_inspired_nav complete_simulation.launch
```

### Scripts not executable
```bash
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws/src/bio_inspired_nav/scripts
chmod +x *.py
```

### TensorFlow errors
```bash
# Fall back to Q-Learning
roslaunch bio_inspired_nav complete_simulation.launch use_ml:=true
# DQN will automatically fallback to Q-Learning if TensorFlow unavailable
```

### No camera image
Check topic:
```bash
rostopic echo /camera/rgb/image_raw
# If no data, ensure robot is spawned correctly
```

## 📚 Paper Implementation

This simulation implements concepts from "Evolutionary Convergence of Multimodal Navigation Algorithms in Mammals and Insects":

1. **Path Integration**: Odometry-based dead reckoning
2. **Scent Tracking**: Gradient-based chemotaxis
3. **Visual Homing**: CNN-based target recognition
4. **Sensor Fusion**: Multi-modal decision making
5. **Adaptive Learning**: Reinforcement learning for optimization

## 🤝 Online Simulation

This simulation is designed for long-duration training suitable for online platforms:
- Headless mode for resource efficiency
- Automated episode management
- Checkpoint saving
- Comprehensive logging
- Minimal human intervention required

### Cloud Training Recommendations
```bash
# Run on AWS/GCP with headless mode
roslaunch bio_inspired_nav complete_simulation.launch \
    gui:=false \
    headless:=true \
    training_mode:=true \
    use_ml:=true
```

## 📄 License

MIT License - Feel free to use for research and education

## 🙏 Acknowledgments

- Bio-inspired algorithms from insect and mammal navigation research
- ROS and Gazebo communities
- TensorFlow and OpenCV projects

## 📞 Support

For issues or questions:
1. Check logs in `/tmp/bio_nav_logs/`
2. Verify all dependencies installed
3. Ensure ROS environment sourced
4. Check Gazebo simulation is running

Happy Navigating! 🤖🧭

# Install missing package
pip3 install pyyaml

# Now run the simulation
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws && source devel/setup.bash && roslaunch bio_inspired_nav simple_simulation.launch