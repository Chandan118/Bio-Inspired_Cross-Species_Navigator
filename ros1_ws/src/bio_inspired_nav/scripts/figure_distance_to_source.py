#!/usr/bin/env python3
"""
Generate Distance to Source Over Time Figure
Shows distance_to_source to highlight approach/divergence behavior
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def generate_distance_to_source_figure():
    """Generate distance to source over time plot"""
    
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
    x = df['x'].values
    y = df['y'].values
    gas_concentration = df['gas_concentration'].values
    linear_vel = df['linear_vel'].values
    angular_vel = df['angular_vel'].values
    
    # Calculate distance to gas source (at 8.0, 8.0)
    distance_to_source = np.sqrt((x - 8.0)**2 + (y - 8.0)**2)
    
    # Normalize timestamp to start from 0
    time_seconds = (timestamp - timestamp[0]) / 1e9  # Convert nanoseconds to seconds
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Plot distance to source over time
    ax.plot(time_seconds, distance_to_source, 'r-', linewidth=1.5, alpha=0.8, label='Distance to Source')
    
    # Add horizontal line for target distance (0.5m - success threshold)
    ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.7, linewidth=1, label='Success Threshold (0.5m)')
    
    # Highlight when robot is close to source (within 2m)
    close_indices = np.where(distance_to_source < 2.0)[0]
    if len(close_indices) > 0:
        ax.scatter(time_seconds[close_indices], distance_to_source[close_indices], 
                  c='orange', s=10, alpha=0.3, label='Near Source (< 2m)', zorder=3)
    
    # Add gas concentration as secondary indicator
    ax2 = ax.twinx()
    ax2.plot(time_seconds, gas_concentration, 'b-', alpha=0.3, linewidth=0.8, label='Gas Concentration')
    ax2.set_ylabel('Gas Concentration', color='b')
    ax2.tick_params(axis='y', labelcolor='b')
    
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Distance to Gas Source (m)', color='r')
    ax.set_title('Distance to Gas Source Over Time - Approach/Divergence Analysis')
    ax.grid(True, alpha=0.3)
    
    # Add legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper right')
    
    # Save the figure
    output_path = '/tmp/bio_nav_distance_to_source.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Distance to source figure saved to: {output_path}")
    print(f"Total time: {time_seconds[-1]:.1f} seconds")
    print(f"Min distance achieved: {np.min(distance_to_source):.2f}m")
    print(f"Final distance: {distance_to_source[-1]:.2f}m")
    print(f"Started at distance: {distance_to_source[0]:.2f}m")
    print(f"Success reached: {np.any(distance_to_source < 0.5)}")


if __name__ == '__main__':
    generate_distance_to_source_figure()