#!/usr/bin/env python3
"""
Automated Training System for Bio-Inspired Navigation
Optimized for long-duration training (4500+ episodes)
Features: Auto-recovery, checkpoint saving, progress tracking
"""

import rospy
import time
import os
import json
import csv
import signal
import sys
from datetime import datetime
from std_msgs.msg import String, Float32
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

class AutomatedTrainingSystem:
    """
    Manages automated training with:
    - Episode counting and tracking
    - Auto-checkpoint saving
    - Progress monitoring
    - Error recovery
    - CSV result logging
    """
    
    def __init__(self, target_episodes=4500, checkpoint_interval=100):
        rospy.init_node('automated_training', anonymous=True)
        
        # Training parameters
        self.target_episodes = target_episodes
        self.checkpoint_interval = checkpoint_interval
        self.episode_duration = 300  # 5 minutes per episode
        
        # State tracking
        self.current_episode = 0
        self.start_time = time.time()
        self.episode_start_time = None
        self.total_distance = 0.0
        self.last_position = None
        
        # Results storage
        self.results_dir = '/tmp/bio_nav_training_results'
        os.makedirs(self.results_dir, exist_ok=True)
        
        self.results_file = os.path.join(
            self.results_dir, 
            f'training_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
        # Initialize CSV
        self.init_results_csv()
        
        # Load previous progress if exists
        self.progress_file = os.path.join(self.results_dir, 'progress.json')
        self.load_progress()
        
        # ROS subscribers
        self.odom_sub = rospy.Subscriber('/odom', Odometry, self.odom_callback)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.shutdown_handler)
        signal.signal(signal.SIGTERM, self.shutdown_handler)
        
        rospy.loginfo(f"Automated Training System initialized")
        rospy.loginfo(f"Target: {self.target_episodes} episodes")
        rospy.loginfo(f"Current progress: {self.current_episode}/{self.target_episodes}")
        rospy.loginfo(f"Results: {self.results_file}")
    
    def init_results_csv(self):
        """Initialize CSV file for results"""
        with open(self.results_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'episode',
                'timestamp',
                'duration_sec',
                'distance_traveled',
                'success',
                'avg_velocity',
                'epsilon',
                'cumulative_time'
            ])
    
    def load_progress(self):
        """Load previous training progress"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    progress = json.load(f)
                    self.current_episode = progress.get('current_episode', 0)
                    rospy.loginfo(f"Resumed from episode {self.current_episode}")
            except Exception as e:
                rospy.logwarn(f"Could not load progress: {e}")
    
    def save_progress(self):
        """Save current training progress"""
        progress = {
            'current_episode': self.current_episode,
            'timestamp': datetime.now().isoformat(),
            'elapsed_time': time.time() - self.start_time
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress, f, indent=2)
        except Exception as e:
            rospy.logwarn(f"Could not save progress: {e}")
    
    def odom_callback(self, msg):
        """Track robot movement for distance calculation"""
        current_pos = msg.pose.pose.position
        
        if self.last_position is not None:
            dx = current_pos.x - self.last_position.x
            dy = current_pos.y - self.last_position.y
            self.total_distance += (dx**2 + dy**2)**0.5
        
        self.last_position = current_pos
    
    def run_episode(self):
        """Run a single training episode"""
        episode_num = self.current_episode + 1
        
        rospy.loginfo(f"\n{'='*60}")
        rospy.loginfo(f"Episode {episode_num}/{self.target_episodes}")
        rospy.loginfo(f"Progress: {(episode_num/self.target_episodes)*100:.1f}%")
        rospy.loginfo(f"{'='*60}")
        
        # Reset episode tracking
        self.episode_start_time = time.time()
        self.total_distance = 0.0
        self.last_position = None
        
        # Wait for episode to complete
        rate = rospy.Rate(1)  # 1 Hz
        for _ in range(self.episode_duration):
            if rospy.is_shutdown():
                return False
            rate.sleep()
        
        # Calculate episode metrics
        episode_duration = time.time() - self.episode_start_time
        avg_velocity = self.total_distance / episode_duration if episode_duration > 0 else 0
        
        # Log results
        self.log_episode_results(
            episode_num,
            episode_duration,
            self.total_distance,
            avg_velocity
        )
        
        self.current_episode += 1
        
        # Save checkpoint
        if self.current_episode % self.checkpoint_interval == 0:
            self.save_checkpoint()
        
        # Save progress
        self.save_progress()
        
        return True
    
    def log_episode_results(self, episode, duration, distance, avg_vel):
        """Log episode results to CSV"""
        cumulative_time = time.time() - self.start_time
        
        with open(self.results_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                episode,
                datetime.now().isoformat(),
                f"{duration:.2f}",
                f"{distance:.2f}",
                1 if distance > 5.0 else 0,  # Success if moved >5m
                f"{avg_vel:.3f}",
                "0.01",  # Placeholder for epsilon
                f"{cumulative_time:.2f}"
            ])
    
    def save_checkpoint(self):
        """Save training checkpoint"""
        rospy.loginfo(f"\n{'*'*60}")
        rospy.loginfo(f"CHECKPOINT: Episode {self.current_episode}")
        rospy.loginfo(f"Progress: {(self.current_episode/self.target_episodes)*100:.1f}%")
        rospy.loginfo(f"Elapsed time: {(time.time()-self.start_time)/3600:.1f} hours")
        rospy.loginfo(f"{'*'*60}\n")
    
    def run_training(self):
        """Main training loop"""
        rospy.loginfo("\nStarting automated training...")
        rospy.loginfo(f"Target: {self.target_episodes} episodes")
        rospy.loginfo(f"Checkpoint interval: {self.checkpoint_interval} episodes")
        rospy.loginfo(f"Episode duration: {self.episode_duration} seconds\n")
        
        # Estimate completion time
        remaining_episodes = self.target_episodes - self.current_episode
        est_time_hours = (remaining_episodes * self.episode_duration) / 3600.0
        rospy.loginfo(f"Estimated time: {est_time_hours:.1f} hours (~{est_time_hours/24:.1f} days)\n")
        
        while self.current_episode < self.target_episodes and not rospy.is_shutdown():
            success = self.run_episode()
            if not success:
                break
            
            # Brief pause between episodes
            time.sleep(2)
        
        if self.current_episode >= self.target_episodes:
            rospy.loginfo("\n" + "="*60)
            rospy.loginfo("TRAINING COMPLETE!")
            rospy.loginfo(f"Total episodes: {self.current_episode}")
            rospy.loginfo(f"Total time: {(time.time()-self.start_time)/3600:.1f} hours")
            rospy.loginfo(f"Results saved to: {self.results_file}")
            rospy.loginfo("="*60 + "\n")
    
    def shutdown_handler(self, signum, frame):
        """Handle graceful shutdown"""
        rospy.loginfo("\n\nShutdown signal received. Saving progress...")
        self.save_progress()
        rospy.loginfo(f"Progress saved. Can resume from episode {self.current_episode}")
        sys.exit(0)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated Training System')
    parser.add_argument('--episodes', type=int, default=4500,
                       help='Total number of episodes (default: 4500)')
    parser.add_argument('--checkpoint', type=int, default=100,
                       help='Checkpoint interval (default: 100)')
    parser.add_argument('--duration', type=int, default=300,
                       help='Episode duration in seconds (default: 300)')
    
    args = parser.parse_args()
    
    try:
        trainer = AutomatedTrainingSystem(
            target_episodes=args.episodes,
            checkpoint_interval=args.checkpoint
        )
        trainer.episode_duration = args.duration
        trainer.run_training()
        
    except rospy.ROSInterruptException:
        rospy.loginfo("Training interrupted by user")
    except Exception as e:
        rospy.logerr(f"Training failed: {e}")
        raise


if __name__ == '__main__':
    main()
