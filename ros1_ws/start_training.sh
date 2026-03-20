#!/bin/bash
# Quick Start Script for Automated Training
# Runs 4500+ episodes with automatic checkpointing

echo "========================================"
echo "Bio-Inspired Navigation - Automated Training"
echo "========================================"
echo ""

# Configuration
EPISODES=${1:-4500}
CHECKPOINT_INTERVAL=${2:-100}
EPISODE_DURATION=${3:-300}

echo "Configuration:"
echo "  - Total Episodes: $EPISODES"
echo "  - Checkpoint Interval: $CHECKPOINT_INTERVAL episodes"
echo "  - Episode Duration: $EPISODE_DURATION seconds"
echo ""

# Calculate estimated time
TOTAL_SECONDS=$((EPISODES * EPISODE_DURATION))
HOURS=$((TOTAL_SECONDS / 3600))
DAYS=$((HOURS / 24))
echo "Estimated Training Time: $HOURS hours (~$DAYS days)"
echo ""

# Setup ROS environment
cd ~/Bio-Inspired_Cross-Species_Navigator/ros1_ws
source /opt/ros/noetic/setup.bash
source devel/setup.bash

echo "Starting simulation..."
echo ""

# Start simulation in background
roslaunch bio_inspired_nav simple_simulation.launch &
SIM_PID=$!

# Wait for ROS to initialize
sleep 10

echo "Starting automated training..."
echo ""

# Start training
rosrun bio_inspired_nav automated_training.py \
    --episodes $EPISODES \
    --checkpoint $CHECKPOINT_INTERVAL \
    --duration $EPISODE_DURATION

# Cleanup
echo ""
echo "Training session ended. Cleaning up..."
kill $SIM_PID 2>/dev/null

echo ""
echo "Results saved to: /tmp/bio_nav_training_results/"
echo "Check progress.json to see current episode count"
echo "To resume training, run this script again"
echo ""
