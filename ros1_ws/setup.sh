#!/bin/bash

# Bio-Inspired Navigation Setup Script
# Automated installation and configuration

set -e

echo "=========================================="
echo "Bio-Inspired Navigation Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check ROS installation
check_ros() {
    echo -e "${YELLOW}Checking ROS installation...${NC}"
    if [ -f "/opt/ros/noetic/setup.bash" ]; then
        ROS_DISTRO="noetic"
        echo -e "${GREEN}Found ROS Noetic${NC}"
    elif [ -f "/opt/ros/melodic/setup.bash" ]; then
        ROS_DISTRO="melodic"
        echo -e "${GREEN}Found ROS Melodic${NC}"
    else
        echo -e "${RED}ROS not found! Please install ROS first.${NC}"
        exit 1
    fi
    
    source /opt/ros/${ROS_DISTRO}/setup.bash
}

# Install dependencies
install_dependencies() {
    echo -e "${YELLOW}Installing dependencies...${NC}"
    
    sudo apt-get update
    sudo apt-get install -y \
        ros-${ROS_DISTRO}-gazebo-ros-pkgs \
        ros-${ROS_DISTRO}-gazebo-ros-control \
        ros-${ROS_DISTRO}-joint-state-publisher \
        ros-${ROS_DISTRO}-robot-state-publisher \
        ros-${ROS_DISTRO}-xacro \
        python3-pip \
        python3-numpy \
        python3-matplotlib \
        python3-opencv \
        python3-scipy
    
    echo -e "${GREEN}System dependencies installed${NC}"
}

# Install Python packages
install_python_packages() {
    echo -e "${YELLOW}Installing Python packages...${NC}"
    
    pip3 install --user \
        opencv-python \
        matplotlib \
        numpy \
        scipy
    
    # Optional: TensorFlow for DQN
    read -p "Install TensorFlow for Deep Q-Learning? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip3 install --user tensorflow==2.8.0 keras
        echo -e "${GREEN}TensorFlow installed${NC}"
    else
        echo -e "${YELLOW}Skipping TensorFlow. Q-Learning will be used instead.${NC}"
    fi
}

# Make scripts executable
make_executable() {
    echo -e "${YELLOW}Making scripts executable...${NC}"
    
    SCRIPT_DIR="$HOME/Bio-Inspired_Cross-Species_Navigator/ros1_ws/src/bio_inspired_nav/scripts"
    
    if [ -d "$SCRIPT_DIR" ]; then
        chmod +x $SCRIPT_DIR/*.py
        echo -e "${GREEN}Scripts are now executable${NC}"
    else
        echo -e "${RED}Scripts directory not found: $SCRIPT_DIR${NC}"
    fi
}

# Build workspace
build_workspace() {
    echo -e "${YELLOW}Building ROS workspace...${NC}"
    
    WS_DIR="$HOME/Bio-Inspired_Cross-Species_Navigator/ros1_ws"
    
    if [ -d "$WS_DIR" ]; then
        cd $WS_DIR
        
        # Clean previous build
        if [ -d "build" ] || [ -d "devel" ]; then
            echo -e "${YELLOW}Cleaning previous build...${NC}"
            rm -rf build devel
        fi
        
        # Build
        catkin_make
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}Workspace built successfully!${NC}"
        else
            echo -e "${RED}Build failed!${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Workspace directory not found: $WS_DIR${NC}"
        exit 1
    fi
}

# Setup environment
setup_environment() {
    echo -e "${YELLOW}Setting up environment...${NC}"
    
    WS_DIR="$HOME/Bio-Inspired_Cross-Species_Navigator/ros1_ws"
    BASHRC="$HOME/.bashrc"
    
    # Check if already sourced
    if grep -q "source $WS_DIR/devel/setup.bash" "$BASHRC"; then
        echo -e "${YELLOW}Workspace already sourced in .bashrc${NC}"
    else
        echo "" >> $BASHRC
        echo "# Bio-Inspired Navigation ROS workspace" >> $BASHRC
        echo "source $WS_DIR/devel/setup.bash" >> $BASHRC
        echo -e "${GREEN}Added workspace to .bashrc${NC}"
    fi
    
    # Source for current session
    source $WS_DIR/devel/setup.bash
}

# Create log directory
create_log_dir() {
    echo -e "${YELLOW}Creating log directory...${NC}"
    
    LOG_DIR="/tmp/bio_nav_logs"
    mkdir -p $LOG_DIR
    
    echo -e "${GREEN}Log directory created: $LOG_DIR${NC}"
}

# Verify installation
verify_installation() {
    echo -e "${YELLOW}Verifying installation...${NC}"
    
    WS_DIR="$HOME/Bio-Inspired_Cross-Species_Navigator/ros1_ws"
    source $WS_DIR/devel/setup.bash
    
    # Check if package is found
    if rospack find bio_inspired_nav > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Package found${NC}"
    else
        echo -e "${RED}✗ Package not found${NC}"
        return 1
    fi
    
    # Check scripts
    SCRIPTS=(
        "bio_navigator_rl.py"
        "vision_processor_cnn.py"
        "gas_plume_tracker.py"
        "gas_sensor_simulator.py"
        "data_logger.py"
        "run_simulation.py"
    )
    
    SCRIPT_DIR="$WS_DIR/src/bio_inspired_nav/scripts"
    for script in "${SCRIPTS[@]}"; do
        if [ -x "$SCRIPT_DIR/$script" ]; then
            echo -e "${GREEN}✓ $script${NC}"
        else
            echo -e "${RED}✗ $script (not executable)${NC}"
        fi
    done
    
    echo -e "${GREEN}Verification complete!${NC}"
}

# Print usage instructions
print_usage() {
    echo ""
    echo "=========================================="
    echo "Setup Complete!"
    echo "=========================================="
    echo ""
    echo -e "${GREEN}Quick Start:${NC}"
    echo "1. Source the workspace:"
    echo "   source ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws/devel/setup.bash"
    echo ""
    echo "2. Launch simulation:"
    echo "   roslaunch bio_inspired_nav complete_simulation.launch"
    echo ""
    echo "3. Or use automated runner:"
    echo "   cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws"
    echo "   python3 src/bio_inspired_nav/scripts/run_simulation.py --training --episodes 10"
    echo ""
    echo -e "${YELLOW}For more information, see:${NC}"
    echo "   ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws/src/bio_inspired_nav/README.md"
    echo ""
}

# Main execution
main() {
    check_ros
    install_dependencies
    install_python_packages
    make_executable
    build_workspace
    setup_environment
    create_log_dir
    verify_installation
    print_usage
}

# Run main function
main
