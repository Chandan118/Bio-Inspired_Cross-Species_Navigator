#!/usr/bin/env python3
"""
Bio-Inspired Navigator with Reinforcement Learning
Implements DQN-based navigation combining multi-sensor fusion
"""

import rospy
import numpy as np
import math
import random
from collections import deque
import pickle
import os

from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan, Imu, Image
from std_msgs.msg import Float32MultiArray, Bool
from nav_msgs.msg import Odometry

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import layers
    HAS_TF = True
except ImportError:
    HAS_TF = False
    rospy.logwarn("TensorFlow not available. Using Q-Learning instead of DQN")


class DQNAgent:
    """Deep Q-Network for navigation decision making"""
    
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # discount rate
        self.epsilon = 1.0   # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()
        
    def _build_model(self):
        """Build neural network for DQN"""
        model = keras.Sequential([
            layers.Dense(64, input_dim=self.state_size, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            layers.Dense(32, activation='relu'),
            layers.Dense(self.action_size, activation='linear')
        ])
        model.compile(loss='mse', optimizer=keras.optimizers.Adam(lr=self.learning_rate))
        return model
    
    def update_target_model(self):
        """Copy weights from model to target_model"""
        self.target_model.set_weights(self.model.get_weights())
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
    
    def act(self, state):
        """Choose action using epsilon-greedy policy"""
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state, verbose=0)
        return np.argmax(act_values[0])
    
    def replay(self, batch_size=32):
        """Train on batch from replay memory"""
        if len(self.memory) < batch_size:
            return
        
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            target = reward
            if not done:
                target = reward + self.gamma * np.amax(
                    self.target_model.predict(next_state, verbose=0)[0])
            target_f = self.model.predict(state, verbose=0)
            target_f[0][action] = target
            self.model.fit(state, target_f, epochs=1, verbose=0)
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def save(self, filepath):
        """Save model weights"""
        self.model.save_weights(filepath)
    
    def load(self, filepath):
        """Load model weights"""
        if os.path.exists(filepath):
            self.model.load_weights(filepath)
            self.update_target_model()


class QLearningAgent:
    """Q-Learning agent as fallback when TensorFlow not available"""
    
    def __init__(self, n_actions=9):
        self.q_table = {}
        self.alpha = 0.1  # learning rate
        self.gamma = 0.95  # discount factor
        self.epsilon = 1.0
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.n_actions = n_actions
    
    def discretize_state(self, state):
        """Convert continuous state to discrete key"""
        discretized = tuple([int(x * 10) / 10.0 for x in state[:10]])
        return discretized
    
    def get_q_value(self, state, action):
        """Get Q-value for state-action pair"""
        state_key = self.discretize_state(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.n_actions)
        return self.q_table[state_key][action]
    
    def act(self, state):
        """Choose action using epsilon-greedy"""
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.n_actions)
        
        state_key = self.discretize_state(state)
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.n_actions)
        return np.argmax(self.q_table[state_key])
    
    def update(self, state, action, reward, next_state, done):
        """Update Q-table using Q-learning update rule"""
        state_key = self.discretize_state(state)
        next_state_key = self.discretize_state(next_state)
        
        if state_key not in self.q_table:
            self.q_table[state_key] = np.zeros(self.n_actions)
        if next_state_key not in self.q_table:
            self.q_table[next_state_key] = np.zeros(self.n_actions)
        
        current_q = self.q_table[state_key][action]
        
        if done:
            target_q = reward
        else:
            target_q = reward + self.gamma * np.max(self.q_table[next_state_key])
        
        self.q_table[state_key][action] = current_q + self.alpha * (target_q - current_q)
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
    
    def save(self, filepath):
        """Save Q-table"""
        with open(filepath, 'wb') as f:
            pickle.dump(self.q_table, f)
    
    def load(self, filepath):
        """Load Q-table"""
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.q_table = pickle.load(f)


class BioInspiredNavigator:
    """
    Bio-inspired navigator with reinforcement learning
    Mimics cross-species navigation strategies from mammals and insects
    """
    
    def __init__(self):
        rospy.init_node('bio_navigator_rl', anonymous=True)
        
        # Parameters
        self.use_ml = rospy.get_param('~use_machine_learning', True)
        self.training_mode = rospy.get_param('~training_mode', True)
        self.model_path = rospy.get_param('~model_path', '/tmp/bio_nav_model')
        
        # State variables
        self.state_size = 15  # [lidar_sectors(8), gas(2), vision(2), odometry(3)]
        self.action_size = 9  # combinations of linear/angular velocities
        
        # Initialize RL agent
        if self.use_ml and HAS_TF:
            rospy.loginfo("Initializing DQN agent with TensorFlow")
            self.agent = DQNAgent(self.state_size, self.action_size)
            try:
                self.agent.load(self.model_path + '.h5')
                rospy.loginfo("Loaded pre-trained DQN model")
            except:
                rospy.loginfo("Starting with fresh DQN model")
        else:
            rospy.loginfo("Initializing Q-Learning agent")
            self.agent = QLearningAgent(self.action_size)
            try:
                self.agent.load(self.model_path + '.pkl')
                rospy.loginfo("Loaded pre-trained Q-table")
            except:
                rospy.loginfo("Starting with fresh Q-table")
        
        # Sensor data
        self.lidar_data = None
        self.imu_data = None
        self.gas_data = [0.0, 0.0]  # [concentration, gradient]
        self.vision_detected = False
        self.vision_offset = 0.0
        self.odom_data = [0.0, 0.0, 0.0]  # [x, y, yaw]
        
        # Navigation state
        self.current_state = np.zeros(self.state_size)
        self.previous_state = None
        self.previous_action = None
        self.goal_position = [5.0, 5.0]  # Default goal
        self.start_position = [0.0, 0.0]
        self.episode_steps = 0
        self.total_reward = 0.0
        
        # Action space: [linear_vel, angular_vel]
        self.actions = [
            [0.3, 0.0],   # forward
            [0.3, 0.5],   # forward-left
            [0.3, -0.5],  # forward-right
            [0.1, 0.8],   # turn left
            [0.1, -0.8],  # turn right
            [0.0, 0.0],   # stop
            [-0.1, 0.0],  # backward
            [0.2, 0.3],   # gentle left
            [0.2, -0.3],  # gentle right
        ]
        
        # Publishers
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.state_pub = rospy.Publisher('/navigator/state', Float32MultiArray, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/scan', LaserScan, self.lidar_callback)
        rospy.Subscriber('/imu', Imu, self.imu_callback)
        rospy.Subscriber('/gas_sensors', Float32MultiArray, self.gas_callback)
        rospy.Subscriber('/vision/target_detected', Bool, self.vision_detected_callback)
        rospy.Subscriber('/vision/target_offset', Float32MultiArray, self.vision_offset_callback)
        rospy.Subscriber('/odom', Odometry, self.odom_callback)
        
        # Control loop
        self.rate = rospy.Rate(10)  # 10 Hz
        self.update_counter = 0
        
        rospy.loginfo("Bio-Inspired Navigator initialized")
    
    def lidar_callback(self, msg):
        """Process LiDAR data - divide into 8 sectors"""
        if len(msg.ranges) == 0:
            return
        
        ranges = np.array(msg.ranges)
        ranges[np.isinf(ranges)] = msg.range_max
        ranges[np.isnan(ranges)] = msg.range_max
        
        # Divide 360 degrees into 8 sectors (45 degrees each)
        sector_size = len(ranges) // 8
        sectors = []
        for i in range(8):
            start = i * sector_size
            end = (i + 1) * sector_size
            sector_min = np.min(ranges[start:end])
            sectors.append(min(sector_min, 10.0) / 10.0)  # Normalize to [0, 1]
        
        self.lidar_data = sectors
    
    def imu_callback(self, msg):
        """Process IMU data"""
        self.imu_data = msg
    
    def gas_callback(self, msg):
        """Process gas sensor data"""
        if len(msg.data) >= 2:
            self.gas_data = [msg.data[0] / 1000.0, msg.data[1] / 100.0]  # Normalize
    
    def vision_detected_callback(self, msg):
        """Process vision detection"""
        self.vision_detected = msg.data
    
    def vision_offset_callback(self, msg):
        """Process vision offset"""
        if len(msg.data) > 0:
            self.vision_offset = msg.data[0]
    
    def odom_callback(self, msg):
        """Process odometry data"""
        self.odom_data[0] = msg.pose.pose.position.x
        self.odom_data[1] = msg.pose.pose.position.y
        
        # Convert quaternion to yaw
        orientation = msg.pose.pose.orientation
        siny_cosp = 2.0 * (orientation.w * orientation.z + orientation.x * orientation.y)
        cosy_cosp = 1.0 - 2.0 * (orientation.y ** 2 + orientation.z ** 2)
        self.odom_data[2] = math.atan2(siny_cosp, cosy_cosp)
    
    def get_state(self):
        """Compile current state from all sensors"""
        state = []
        
        # LiDAR sectors (8 values)
        if self.lidar_data is not None:
            state.extend(self.lidar_data)
        else:
            state.extend([1.0] * 8)
        
        # Gas sensors (2 values)
        state.extend(self.gas_data)
        
        # Vision (2 values: detected, offset)
        state.append(1.0 if self.vision_detected else 0.0)
        state.append(self.vision_offset)
        
        # Odometry relative to goal (3 values: dx, dy, d_theta)
        dx = self.goal_position[0] - self.odom_data[0]
        dy = self.goal_position[1] - self.odom_data[1]
        distance = math.sqrt(dx**2 + dy**2)
        angle_to_goal = math.atan2(dy, dx)
        angle_diff = self.normalize_angle(angle_to_goal - self.odom_data[2])
        
        state.append(distance / 10.0)  # Normalize
        state.append(angle_diff / math.pi)  # Normalize to [-1, 1]
        state.append(self.odom_data[2] / math.pi)  # Current heading
        
        return np.array(state)
    
    def calculate_reward(self, state, action):
        """Calculate reward for current state-action pair"""
        reward = 0.0
        
        # Distance to goal reward
        distance = state[13] * 10.0  # Denormalize
        reward -= distance * 0.1  # Penalty for being far from goal
        
        # Progress reward
        if self.previous_state is not None:
            prev_distance = self.previous_state[13] * 10.0
            if distance < prev_distance:
                reward += 1.0  # Reward for getting closer
        
        # Obstacle avoidance
        min_obstacle_dist = min(state[:8]) * 10.0
        if min_obstacle_dist < 0.5:
            reward -= 5.0  # Large penalty for being too close to obstacles
        elif min_obstacle_dist < 1.0:
            reward -= 2.0  # Smaller penalty for being somewhat close
        
        # Gas tracking reward (scent following)
        if state[8] > 0.5:  # High gas concentration
            reward += 2.0
        if state[9] > 0:  # Positive gradient
            reward += 1.0
        
        # Vision target reward
        if state[10] > 0.5:  # Target detected
            reward += 3.0
            # Bonus for being aligned with target
            if abs(state[11]) < 0.2:
                reward += 2.0
        
        # Goal reached
        if distance < 0.5:
            reward += 100.0
            rospy.loginfo("Goal reached! Episode reward: {}".format(self.total_reward + reward))
        
        # Movement efficiency
        linear_vel, angular_vel = self.actions[action]
        reward -= abs(angular_vel) * 0.05  # Small penalty for turning
        
        return reward
    
    def normalize_angle(self, angle):
        """Normalize angle to [-pi, pi]"""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    def execute_action(self, action):
        """Execute selected action"""
        linear_vel, angular_vel = self.actions[action]
        
        twist = Twist()
        twist.linear.x = linear_vel
        twist.angular.z = angular_vel
        self.cmd_vel_pub.publish(twist)
    
    def check_done(self, state):
        """Check if episode is done"""
        distance = state[13] * 10.0
        min_obstacle_dist = min(state[:8]) * 10.0
        
        # Goal reached
        if distance < 0.5:
            return True
        
        # Collision
        if min_obstacle_dist < 0.3:
            return True
        
        # Max steps
        if self.episode_steps > 1000:
            return True
        
        return False
    
    def run(self):
        """Main control loop"""
        rospy.loginfo("Starting navigation loop...")
        
        while not rospy.is_shutdown():
            # Get current state
            self.current_state = self.get_state()
            
            # Choose action
            if self.use_ml and HAS_TF:
                state_reshaped = np.reshape(self.current_state, [1, self.state_size])
                action = self.agent.act(state_reshaped)
            else:
                action = self.agent.act(self.current_state)
            
            # Execute action
            self.execute_action(action)
            
            # Wait for next cycle
            self.rate.sleep()
            
            # Get next state
            next_state = self.get_state()
            
            # Calculate reward
            reward = self.calculate_reward(next_state, action)
            self.total_reward += reward
            
            # Check if done
            done = self.check_done(next_state)
            
            # Learn (if training)
            if self.training_mode:
                if self.use_ml and HAS_TF:
                    state_reshaped = np.reshape(self.current_state, [1, self.state_size])
                    next_state_reshaped = np.reshape(next_state, [1, self.state_size])
                    self.agent.remember(state_reshaped, action, reward, next_state_reshaped, done)
                    self.agent.replay(32)
                else:
                    self.agent.update(self.current_state, action, reward, next_state, done)
            
            # Update for next iteration
            self.previous_state = self.current_state.copy()
            self.previous_action = action
            self.episode_steps += 1
            self.update_counter += 1
            
            # Periodic model updates
            if self.use_ml and HAS_TF and self.update_counter % 100 == 0:
                self.agent.update_target_model()
            
            # Save model periodically
            if self.training_mode and self.update_counter % 500 == 0:
                if self.use_ml and HAS_TF:
                    self.agent.save(self.model_path + '.h5')
                else:
                    self.agent.save(self.model_path + '.pkl')
                rospy.loginfo("Model saved. Steps: {}, Total reward: {:.2f}, Epsilon: {:.3f}".format(
                    self.update_counter, self.total_reward, self.agent.epsilon))
            
            # Reset if done
            if done:
                rospy.loginfo("Episode finished. Steps: {}, Total reward: {:.2f}".format(
                    self.episode_steps, self.total_reward))
                self.episode_steps = 0
                self.total_reward = 0.0
                # Reset robot position (in real scenario, you'd reset in Gazebo)
            
            # Publish state for monitoring
            state_msg = Float32MultiArray()
            state_msg.data = self.current_state.tolist()
            self.state_pub.publish(state_msg)
        
        # Save final model
        if self.training_mode:
            if self.use_ml and HAS_TF:
                self.agent.save(self.model_path + '.h5')
            else:
                self.agent.save(self.model_path + '.pkl')
            rospy.loginfo("Final model saved")


if __name__ == '__main__':
    try:
        navigator = BioInspiredNavigator()
        navigator.run()
    except rospy.ROSInterruptException:
        pass
