#!/usr/bin/env python3
"""
Generate Gas Gradient vs. Robot Heading Figure
Compares gas_gradient with yaw (robot heading)
Shows alignment during plume tracking
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def generate_gas_gradient_heading_figure():
    """Generate gas gradient vs robot heading plot"""
    
    # Find the latest simulation log
    log_files = glob.glob('/tmp/bio_nav_logs/nav_log_*.csv')
    if not log_files:
        print("No simulation logs found!")
        return
    
    latest_log = max(log_files, key=os.path.getctime)
    print(f"Loading data from: {latest_log}")
    
    # Load the data
    df = pd.read_csv(latest_log)
    
    # Extract data
    timestamp = df['timestamp'].values
    gas_concentration = df['gas_concentration'].values
    gas_gradient = df['gas_gradient'].values if 'gas_gradient' in df.columns else None
    yaw = df['yaw'].values
    x = df['x'].values
    y = df['y'].values
    
    # Calculate distance to source
    distance_to_source = np.sqrt((x - 8.0)**2 + (y - 8.0)**2)
    
    # Normalize timestamp to start from 0
    time_seconds = (timestamp - timestamp[0]) / 1e9  # Convert nanoseconds to seconds
    
    # If gas_gradient column doesn't exist, create it from position changes
    if gas_gradient is None or np.all(np.isnan(gas_gradient)):
        # Calculate gas gradient as the direction toward higher gas concentration
        # Use a simple derivative approach
        gas_gradient = np.zeros_like(gas_concentration)
        for i in range(1, len(gas_concentration)-1):
            # Simple gradient calculation
            gas_gradient[i] = (gas_concentration[i+1] - gas_concentration[i-1]) / 2.0
        gas_gradient[0] = gas_gradient[1]
        gas_gradient[-1] = gas_gradient[-2]
    
    # Calculate gas source direction (direction from robot to source)
    gas_source_direction = np.arctan2(8.0 - y, 8.0 - x)  # Angle to source
    
    # Calculate alignment between robot heading and gas source direction
    heading_alignment = np.cos(yaw - gas_source_direction)
    
    # Calculate alignment between robot heading and gas gradient direction
    # Assuming gas_gradient represents the direction of increasing concentration
    gradient_alignment = np.cos(yaw - gas_gradient)
    
    # Create the plot
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Robot heading vs gas source direction
    ax1.plot(time_seconds, yaw, 'b-', alpha=0.6, label='Robot Yaw', linewidth=1)
    ax1.plot(time_seconds, gas_source_direction, 'g-', alpha=0.6, label='Gas Source Direction', linewidth=1)
    ax1.set_xlabel('Time (seconds)')
    ax1.set_ylabel('Angle (rad)')
    ax1.set_title('Robot Heading vs Gas Source Direction')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    
    # Plot 2: Alignment between heading and gas source direction
    ax2.plot(time_seconds, heading_alignment, 'purple', alpha=0.8, linewidth=1)
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Alignment (cosine)')
    ax2.set_title('Robot Heading Alignment with Gas Source Direction')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='r', linestyle='--', label='No Alignment')
    ax2.axhline(y=1, color='g', linestyle='--', label='Perfect Alignment')
    ax2.axhline(y=-1, color='r', linestyle='--')
    ax2.legend()
    
    # Plot 3: Gas concentration and gradient
    ax3.plot(time_seconds, gas_concentration, 'orange', label='Gas Concentration', linewidth=1)
    ax3_twin = ax3.twinx()
    ax3_twin.plot(time_seconds, gas_gradient, 'navy', label='Gas Gradient', linewidth=0.8)
    ax3.set_xlabel('Time (seconds)')
    ax3.set_ylabel('Gas Concentration', color='orange')
    ax3_twin.set_ylabel('Gas Gradient', color='navy')
    ax3.set_title('Gas Concentration and Gradient Over Time')
    ax3.grid(True, alpha=0.3)
    
    # Create legends for ax3
    ax3.legend(loc='upper left')
    ax3_twin.legend(loc='upper right')
    
    # Plot 4: Alignment between heading and gas gradient
    ax4.plot(time_seconds, gradient_alignment, 'red', linewidth=1, label='Gradient Alignment')
    ax4_twin = ax4.twinx()
    ax4_twin.plot(time_seconds, distance_to_source, 'brown', linewidth=0.8, label='Distance to Source')
    ax4.set_xlabel('Time (seconds)')
    ax4.set_ylabel('Gradient Alignment', color='red')
    ax4_twin.set_ylabel('Distance to Source (m)', color='brown')
    ax4.set_title('Robot Heading Alignment with Gas Gradient')
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='--', label='No Alignment')
    ax4.axhline(y=1, color='green', linestyle='--', label='Perfect Alignment')
    ax4.axhline(y=-1, color='red', linestyle='--', label='Opposite')
    
    # Create legends for ax4
    ax4.legend(loc='upper left')
    ax4_twin.legend(loc='upper right')
    
    plt.tight_layout()
    
    # Save the figure
    output_path = '/tmp/bio_nav_gas_gradient_heading.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Gas gradient vs heading figure saved to: {output_path}")
    print(f"Total time: {time_seconds[-1]:.1f} seconds")
    print(f"Mean heading alignment with gas source: {np.mean(heading_alignment):.3f}")
    print(f"Mean gradient alignment: {np.mean(gradient_alignment):.3f}")
    print(f"Alignment variance: {np.var(gradient_alignment):.3f}")
    print(f"Time spent with good alignment (>0.5): {np.sum(np.abs(gradient_alignment) > 0.5) / len(gradient_alignment) * 100:.1f}%")


if __name__ == '__main__':
    generate_gas_gradient_heading_figure()