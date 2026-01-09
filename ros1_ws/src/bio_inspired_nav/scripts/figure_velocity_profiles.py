#!/usr/bin/env python3
"""
Generate Velocity Profiles Figure
Shows linear and angular velocity over time
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def generate_velocity_profiles_figure():
    """Generate velocity profiles over time"""
    
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
    linear_vel = df['linear_vel'].values
    angular_vel = df['angular_vel'].values
    gas_concentration = df['gas_concentration'].values
    distance_to_source = np.sqrt((df['x'] - 8.0)**2 + (df['y'] - 8.0)**2).values
    
    # Normalize timestamp to start from 0
    time_seconds = (timestamp - timestamp[0]) / 1e9  # Convert nanoseconds to seconds
    
    # Create the plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    # Plot linear velocity
    ax1.plot(time_seconds, linear_vel, 'b-', linewidth=1.0, alpha=0.8, label='Linear Velocity')
    
    # Highlight when robot is tracking gas (high gas concentration)
    gas_tracking_indices = np.where(gas_concentration > 100)[0]
    if len(gas_tracking_indices) > 0:
        ax1.scatter(time_seconds[gas_tracking_indices], linear_vel[gas_tracking_indices], 
                   c='orange', s=8, alpha=0.4, label='Gas Tracking (>100)', zorder=3)
    
    ax1.set_ylabel('Linear Velocity (m/s)', fontsize=12)
    ax1.set_title('Velocity Profiles - Linear and Angular Velocities Over Time')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    
    # Plot angular velocity
    ax2.plot(time_seconds, angular_vel, 'r-', linewidth=1.0, alpha=0.8, label='Angular Velocity')
    
    # Highlight turning behavior when tracking gas
    if len(gas_tracking_indices) > 0:
        ax2.scatter(time_seconds[gas_tracking_indices], angular_vel[gas_tracking_indices], 
                   c='orange', s=8, alpha=0.4, label='Gas Tracking (>100)', zorder=3)
    
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('Angular Velocity (rad/s)', fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right')
    
    # Add gas concentration as background
    ax1_2 = ax1.twinx()
    ax1_2.plot(time_seconds, gas_concentration, 'g-', alpha=0.2, linewidth=0.5)
    ax1_2.set_ylabel('Gas Concentration', color='g')
    ax1_2.tick_params(axis='y', labelcolor='g')
    
    ax2_2 = ax2.twinx()
    ax2_2.plot(time_seconds, distance_to_source, 'purple', alpha=0.2, linewidth=0.5)
    ax2_2.set_ylabel('Distance to Source (m)', color='purple')
    ax2_2.tick_params(axis='y', labelcolor='purple')
    
    plt.tight_layout()
    
    # Save the figure
    output_path = '/tmp/bio_nav_velocity_profiles.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Velocity profiles figure saved to: {output_path}")
    print(f"Total time: {time_seconds[-1]:.1f} seconds")
    print(f"Linear velocity range: {np.min(linear_vel):.3f} to {np.max(linear_vel):.3f} m/s")
    print(f"Angular velocity range: {np.min(angular_vel):.3f} to {np.max(angular_vel):.3f} rad/s")
    print(f"Mean linear velocity: {np.mean(np.abs(linear_vel)):.3f} m/s")
    print(f"Mean angular velocity: {np.mean(np.abs(angular_vel)):.3f} rad/s")


if __name__ == '__main__':
    generate_velocity_profiles_figure()