#!/usr/bin/env python3
"""
Vision Processor with CNN-based Object Detection
Uses pre-trained models for target recognition
"""

import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from std_msgs.msg import Bool, Float32MultiArray
from geometry_msgs.msg import Point

try:
    import tensorflow as tf
    from tensorflow import keras
    HAS_TF = True
except ImportError:
    HAS_TF = False
    rospy.logwarn("TensorFlow not available. Using traditional CV only")


class VisionProcessorCNN:
    """
    Advanced vision processing using CNNs for object detection
    Falls back to color-based detection if ML unavailable
    """
    
    def __init__(self):
        rospy.init_node('vision_processor_cnn', anonymous=True)
        
        # Parameters
        self.use_cnn = rospy.get_param('~use_cnn', True) and HAS_TF
        self.target_class = rospy.get_param('~target_class', 'bottle')
        self.confidence_threshold = rospy.get_param('~confidence_threshold', 0.5)
        self.target_color_hsv = rospy.get_param('~target_color_hsv', [20, 80, 80])  # Orange
        self.color_tolerance = rospy.get_param('~color_tolerance', [15, 50, 50])
        
        self.bridge = CvBridge()
        self.model = None
        
        # Load pre-trained model if using CNN
        if self.use_cnn:
            try:
                # Using MobileNetV2 for efficient object detection
                self.model = keras.applications.MobileNetV2(
                    weights='imagenet',
                    include_top=True,
                    input_shape=(224, 224, 3)
                )
                self.model.trainable = False
                rospy.loginfo("Loaded MobileNetV2 model for vision processing")
            except Exception as e:
                rospy.logwarn("Failed to load CNN model: {}. Using color detection".format(e))
                self.use_cnn = False
        
        # Publishers
        self.detected_pub = rospy.Publisher('/vision/target_detected', Bool, queue_size=10)
        self.offset_pub = rospy.Publisher('/vision/target_offset', Float32MultiArray, queue_size=10)
        self.debug_image_pub = rospy.Publisher('/vision/debug_image', Image, queue_size=1)
        self.bbox_pub = rospy.Publisher('/vision/bounding_box', Point, queue_size=10)
        
        # Subscribers
        rospy.Subscriber('/camera/rgb/image_raw', Image, self.image_callback, queue_size=1)
        
        rospy.loginfo("Vision Processor CNN initialized")
    
    def preprocess_for_cnn(self, image):
        """Preprocess image for CNN input"""
        # Resize to model input size
        resized = cv2.resize(image, (224, 224))
        # Normalize
        normalized = resized.astype(np.float32) / 255.0
        # Add batch dimension
        batched = np.expand_dims(normalized, axis=0)
        return batched
    
    def detect_with_cnn(self, image):
        """Detect objects using CNN"""
        preprocessed = self.preprocess_for_cnn(image)
        
        # Get predictions
        predictions = self.model.predict(preprocessed, verbose=0)
        
        # Decode predictions (top 5 classes)
        decoded = keras.applications.mobilenet_v2.decode_predictions(predictions, top=5)[0]
        
        # Check if target class is detected
        for class_id, class_name, confidence in decoded:
            if self.target_class.lower() in class_name.lower():
                if confidence >= self.confidence_threshold:
                    return True, confidence, class_name
        
        return False, 0.0, None
    
    def detect_with_color(self, image):
        """Fallback color-based detection"""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Define color range
        h, s, v = self.target_color_hsv
        h_tol, s_tol, v_tol = self.color_tolerance
        
        lower_bound = np.array([max(0, h - h_tol), max(0, s - s_tol), max(0, v - v_tol)])
        upper_bound = np.array([min(179, h + h_tol), 255, 255])
        
        # Create mask
        mask = cv2.inRange(hsv, lower_bound, upper_bound)
        
        # Morphological operations to remove noise
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return False, None, None
        
        # Find largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        
        if area < 500:  # Minimum area threshold
            return False, None, None
        
        # Get bounding box
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        return True, (x, y, w, h), mask
    
    def calculate_offset(self, bbox, image_width):
        """Calculate horizontal offset from image center"""
        if bbox is None:
            return 0.0
        
        x, y, w, h = bbox
        center_x = x + w / 2
        
        # Normalize to [-1, 1]
        offset = (2.0 * center_x / image_width) - 1.0
        
        return offset
    
    def image_callback(self, msg):
        """Process incoming images"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except CvBridgeError as e:
            rospy.logerr("CV Bridge Error: {}".format(e))
            return
        
        height, width = cv_image.shape[:2]
        detected = False
        bbox = None
        debug_image = cv_image.copy()
        
        # Try CNN detection first
        if self.use_cnn:
            detected, confidence, class_name = self.detect_with_cnn(cv_image)
            
            if detected:
                # For CNN, we don't have precise bbox, so use whole image center
                # In production, use object detection model like YOLO or SSD
                text = "{}: {:.2f}%".format(class_name, confidence * 100)
                cv2.putText(debug_image, text, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                # Draw indicator
                cv2.circle(debug_image, (width // 2, height // 2), 50, (0, 255, 0), 3)
        
        # Fallback or supplement with color detection
        if not detected:
            detected, bbox, mask = self.detect_with_color(cv_image)
            
            if detected and bbox is not None:
                x, y, w, h = bbox
                
                # Draw bounding box
                cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Draw center point
                center_x = x + w // 2
                center_y = y + h // 2
                cv2.circle(debug_image, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Draw crosshair
                cv2.line(debug_image, (center_x - 20, center_y), (center_x + 20, center_y), (0, 255, 255), 2)
                cv2.line(debug_image, (center_x, center_y - 20), (center_x, center_y + 20), (0, 255, 255), 2)
                
                # Publish bounding box center
                bbox_msg = Point()
                bbox_msg.x = float(center_x)
                bbox_msg.y = float(center_y)
                bbox_msg.z = float(w * h)  # Area
                self.bbox_pub.publish(bbox_msg)
        
        # Calculate offset
        if detected:
            if bbox is not None:
                offset = self.calculate_offset(bbox, width)
                x, y, w, h = bbox
                distance_estimate = 1000.0 / (w * h) if (w * h) > 0 else 10.0  # Rough estimate
            else:
                offset = 0.0  # CNN detection without precise bbox
                distance_estimate = 5.0
        else:
            offset = 0.0
            distance_estimate = 10.0
        
        # Publish detection result
        self.detected_pub.publish(Bool(data=detected))
        
        # Publish offset and distance
        offset_msg = Float32MultiArray()
        offset_msg.data = [offset, distance_estimate]
        self.offset_pub.publish(offset_msg)
        
        # Add status text to debug image
        status_text = "DETECTED" if detected else "SEARCHING"
        color = (0, 255, 0) if detected else (0, 0, 255)
        cv2.putText(debug_image, status_text, (10, height - 20),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        
        # Draw center line for reference
        cv2.line(debug_image, (width // 2, 0), (width // 2, height), (255, 0, 0), 1)
        
        # Publish debug image
        try:
            debug_msg = self.bridge.cv2_to_imgmsg(debug_image, "bgr8")
            self.debug_image_pub.publish(debug_msg)
        except CvBridgeError as e:
            rospy.logerr("Failed to publish debug image: {}".format(e))
    
    def run(self):
        """Main loop"""
        rospy.spin()


if __name__ == '__main__':
    try:
        processor = VisionProcessorCNN()
        processor.run()
    except rospy.ROSInterruptException:
        pass
