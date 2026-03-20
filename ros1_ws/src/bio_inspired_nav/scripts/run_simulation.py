#!/usr/bin/env python3
"""
Simulation Runner for Bio-Inspired Navigation
Handles training episodes, evaluation, and result generation
"""

import rospy
import subprocess
import time
import os
import sys
import signal
import argparse
import matplotlib.pyplot as plt
import numpy as np
from geometry_msgs.msg import Twist
from std_msgs.msg import Empty
from gazebo_msgs.srv import SetModelState
from gazebo_msgs.msg import ModelState


class SimulationRunner:
    """
    Manages simulation runs, training episodes, and evaluation
    """
    
    def __init__(self, args):
        self.args = args
        self.processes = []
        self.episode_count = 0
        self.results = {
            'episode': [],
            'success': [],
            'time_taken': [],
            'distance_traveled': [],
            'min_distance_to_goal': [],
            'final_gas_concentration': []
        }
        
        # ROS initialization
        rospy.init_node('simulation_runner', anonymous=True)
        
        # Publishers for control
        self.reset_pub = rospy.Publisher('/simulation/reset', Empty, queue_size=10)
        
        rospy.loginfo("Simulation Runner initialized")
    
    def start_gazebo(self):
        """Start Gazebo simulation"""
        rospy.loginfo("Starting Gazebo...")
        
        cmd = [
            'roslaunch',
            'bio_inspired_nav',
            'complete_simulation.launch',
            f'gui:={str(self.args.gui).lower()}',
            f'headless:={str(self.args.headless).lower()}',
            f'use_ml:={str(self.args.use_ml).lower()}',
            f'training_mode:={str(self.args.training).lower()}'
        ]
        
        process = subprocess.Popen(cmd)
        self.processes.append(process)
        
        # Wait for Gazebo to initialize
        rospy.loginfo("Waiting for Gazebo to initialize...")
        time.sleep(10)
        rospy.loginfo("Gazebo ready!")
        
        return process
    
    def start_data_logger(self):
        """Start data logging node"""
        rospy.loginfo("Starting data logger...")
        
        cmd = [
            'rosrun',
            'bio_inspired_nav',
            'data_logger.py',
            f'_log_dir:={self.args.log_dir}',
            f'_enable_plotting:={str(self.args.plot).lower()}'
        ]
        
        process = subprocess.Popen(cmd)
        self.processes.append(process)
        time.sleep(2)
        
        return process
    
    def reset_simulation(self):
        """Reset robot to starting position"""
        rospy.loginfo("Resetting simulation...")
        
        try:
            rospy.wait_for_service('/gazebo/set_model_state', timeout=5.0)
            set_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
            
            state = ModelState()
            state.model_name = 'bio_robot'
            state.pose.position.x = 0.0
            state.pose.position.y = 0.0
            state.pose.position.z = 0.1
            state.pose.orientation.x = 0.0
            state.pose.orientation.y = 0.0
            state.pose.orientation.z = 0.0
            state.pose.orientation.w = 1.0
            
            set_state(state)
            rospy.loginfo("Robot reset to starting position")
            
        except Exception as e:
            rospy.logwarn(f"Failed to reset simulation: {e}")
    
    def run_episode(self, episode_num):
        """Run a single training/evaluation episode"""
        rospy.loginfo(f"Starting Episode {episode_num}")
        
        start_time = time.time()
        self.reset_simulation()
        
        # Wait for episode to complete (timeout or goal reached)
        episode_duration = self.args.episode_duration
        rate = rospy.Rate(1)  # 1 Hz
        
        for _ in range(int(episode_duration)):
            if rospy.is_shutdown():
                break
            rate.sleep()
        
        elapsed_time = time.time() - start_time
        
        # Collect episode results (simplified - in real implementation, collect from topics)
        self.results['episode'].append(episode_num)
        self.results['time_taken'].append(elapsed_time)
        # Other metrics would be collected from actual topic data
        
        rospy.loginfo(f"Episode {episode_num} completed in {elapsed_time:.2f} seconds")
    
    def run_training(self):
        """Run multiple training episodes"""
        rospy.loginfo(f"Starting training for {self.args.episodes} episodes")
        
        for episode in range(self.args.episodes):
            self.run_episode(episode + 1)
            
            # Save checkpoint every N episodes
            if (episode + 1) % 10 == 0:
                self.save_checkpoint(episode + 1)
        
        rospy.loginfo("Training completed!")
        self.generate_results()
    
    def run_evaluation(self):
        """Run evaluation mode (no learning)"""
        rospy.loginfo("Running evaluation mode")
        
        for episode in range(self.args.eval_episodes):
            self.run_episode(episode + 1)
        
        rospy.loginfo("Evaluation completed!")
        self.generate_results()
    
    def save_checkpoint(self, episode):
        """Save training checkpoint"""
        rospy.loginfo(f"Saving checkpoint at episode {episode}")
        # Model saving is handled by the RL nodes themselves
    
    def generate_results(self):
        """Generate and save result plots"""
        rospy.loginfo("Generating result plots...")
        
        if len(self.results['episode']) == 0:
            rospy.logwarn("No episodes completed")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Bio-Inspired Navigation - Training Results', fontsize=16)
        
        # Plot 1: Time per episode
        axes[0, 0].plot(self.results['episode'], self.results['time_taken'], 'b-o')
        axes[0, 0].set_xlabel('Episode')
        axes[0, 0].set_ylabel('Time (seconds)')
        axes[0, 0].set_title('Episode Duration')
        axes[0, 0].grid(True)
        
        # Plot 2: Success rate (rolling average)
        if len(self.results['success']) > 0:
            window = 10
            success_rate = np.convolve(self.results['success'], 
                                      np.ones(window)/window, mode='valid')
            axes[0, 1].plot(range(window-1, len(self.results['success'])), 
                          success_rate * 100, 'g-')
            axes[0, 1].set_xlabel('Episode')
            axes[0, 1].set_ylabel('Success Rate (%)')
            axes[0, 1].set_title(f'Success Rate (Rolling Avg, window={window})')
            axes[0, 1].grid(True)
        
        # Plot 3: Distance traveled
        if len(self.results['distance_traveled']) > 0:
            axes[1, 0].plot(self.results['episode'], 
                          self.results['distance_traveled'], 'r-o')
            axes[1, 0].set_xlabel('Episode')
            axes[1, 0].set_ylabel('Distance (meters)')
            axes[1, 0].set_title('Total Distance Traveled')
            axes[1, 0].grid(True)
        
        # Plot 4: Minimum distance to goal
        if len(self.results['min_distance_to_goal']) > 0:
            axes[1, 1].plot(self.results['episode'], 
                          self.results['min_distance_to_goal'], 'm-o')
            axes[1, 1].set_xlabel('Episode')
            axes[1, 1].set_ylabel('Distance (meters)')
            axes[1, 1].set_title('Closest Approach to Goal')
            axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        # Save figure
        result_file = os.path.join(self.args.log_dir, 'training_results.png')
        plt.savefig(result_file, dpi=300)
        rospy.loginfo(f"Results saved to: {result_file}")
        
        if self.args.plot:
            plt.show()
    
    def cleanup(self):
        """Clean up all processes"""
        rospy.loginfo("Cleaning up...")
        
        for process in self.processes:
            try:
                process.send_signal(signal.SIGINT)
                process.wait(timeout=5)
            except:
                process.kill()
        
        rospy.loginfo("Cleanup complete")
    
    def run(self):
        """Main execution"""
        try:
            # Start simulation
            self.start_gazebo()
            
            # Start data logger
            if self.args.log:
                self.start_data_logger()
            
            # Wait for everything to initialize
            time.sleep(5)
            
            # Run training or evaluation
            if self.args.training:
                self.run_training()
            else:
                self.run_evaluation()
            
        except KeyboardInterrupt:
            rospy.loginfo("Interrupted by user")
        except Exception as e:
            rospy.logerr(f"Error: {e}")
        finally:
            self.cleanup()


def main():
    parser = argparse.ArgumentParser(description='Bio-Inspired Navigation Simulation Runner')
    
    # Simulation settings
    parser.add_argument('--episodes', type=int, default=50,
                       help='Number of training episodes')
    parser.add_argument('--eval-episodes', type=int, default=10,
                       help='Number of evaluation episodes')
    parser.add_argument('--episode-duration', type=int, default=300,
                       help='Maximum duration per episode (seconds)')
    
    # Mode settings
    parser.add_argument('--training', action='store_true',
                       help='Run in training mode')
    parser.add_argument('--evaluation', action='store_true',
                       help='Run in evaluation mode (no learning)')
    parser.add_argument('--use-ml', action='store_true', default=True,
                       help='Use machine learning algorithms')
    
    # Visualization settings
    parser.add_argument('--gui', action='store_true', default=True,
                       help='Show Gazebo GUI')
    parser.add_argument('--headless', action='store_true',
                       help='Run Gazebo in headless mode')
    parser.add_argument('--plot', action='store_true', default=True,
                       help='Show real-time plots')
    
    # Logging settings
    parser.add_argument('--log', action='store_true', default=True,
                       help='Enable data logging')
    parser.add_argument('--log-dir', type=str, default='/tmp/bio_nav_logs',
                       help='Directory for log files')
    
    args = parser.parse_args()
    
    # Create log directory
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
    
    # Run simulation
    runner = SimulationRunner(args)
    runner.run()


if __name__ == '__main__':
    main()
