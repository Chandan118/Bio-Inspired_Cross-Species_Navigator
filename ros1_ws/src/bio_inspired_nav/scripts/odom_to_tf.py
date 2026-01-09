#!/usr/bin/env python3
"""
Odometry to TF Broadcaster
Publishes TF transforms based on odometry data
"""

import rospy
import tf
from nav_msgs.msg import Odometry

class OdomToTF:
    def __init__(self):
        rospy.init_node('odom_to_tf', anonymous=False)
        
        self.tf_broadcaster = tf.TransformBroadcaster()
        
        # Subscribe to odometry
        self.odom_sub = rospy.Subscriber('/odom', Odometry, self.odom_callback, queue_size=1)
        
        rospy.loginfo("Odometry to TF broadcaster started")
        
    def odom_callback(self, msg):
        """Broadcast TF based on odometry"""
        # Extract position and orientation
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        
        # Broadcast odom -> base_footprint transform
        self.tf_broadcaster.sendTransform(
            (position.x, position.y, position.z),
            (orientation.x, orientation.y, orientation.z, orientation.w),
            rospy.Time.now(),
            "base_footprint",
            "odom"
        )
    
    def run(self):
        rospy.spin()

if __name__ == '__main__':
    try:
        node = OdomToTF()
        node.run()
    except rospy.ROSInterruptException:
        pass
