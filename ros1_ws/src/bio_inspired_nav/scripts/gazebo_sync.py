#!/usr/bin/env python3
"""
Gazebo Synchronizer - Updates Gazebo robot position based on /odom topic
This allows visualization of the running simulation in Gazebo
"""

import rospy
from nav_msgs.msg import Odometry
from gazebo_msgs.srv import SetModelState
from gazebo_msgs.msg import ModelState
from geometry_msgs.msg import Pose, Twist
import sys

class GazeboSync:
    def __init__(self):
        rospy.init_node('gazebo_sync', anonymous=False)
        
        # Wait for Gazebo services
        rospy.loginfo("Waiting for Gazebo services...")
        rospy.wait_for_service('/gazebo/set_model_state', timeout=10.0)
        
        self.set_model_state = rospy.ServiceProxy('/gazebo/set_model_state', SetModelState)
        
        # Subscribe to odometry from simulation
        self.odom_sub = rospy.Subscriber('/odom', Odometry, self.odom_callback, queue_size=1)
        
        self.rate = rospy.Rate(10)  # 10 Hz update
        
        rospy.loginfo("Gazebo Synchronizer started - Visualizing robot movement")
        
    def odom_callback(self, msg):
        """Update Gazebo robot position based on odometry"""
        try:
            # Create model state
            model_state = ModelState()
            model_state.model_name = 'bio_robot'
            model_state.pose = msg.pose.pose
            model_state.twist = msg.twist.twist
            model_state.reference_frame = 'world'
            
            # Update Gazebo
            self.set_model_state(model_state)
            
        except rospy.ServiceException as e:
            rospy.logwarn_throttle(5.0, "Service call failed: {}".format(e))
        except Exception as e:
            rospy.logwarn_throttle(5.0, "Error updating Gazebo: {}".format(e))
    
    def run(self):
        rospy.spin()

if __name__ == '__main__':
    try:
        sync = GazeboSync()
        sync.run()
    except rospy.ROSInterruptException:
        pass
    except KeyboardInterrupt:
        rospy.loginfo("Gazebo Synchronizer shutdown")
