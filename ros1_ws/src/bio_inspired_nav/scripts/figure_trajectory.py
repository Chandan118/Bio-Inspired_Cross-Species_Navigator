#!/usr/bin/env python3
"""
Generate Robot Trajectory Figure
Shows (x, y) path with start/end points and gas concentration overlay
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def generate_trajectory_figure():
    """Generate robot trajectory plot with gas concentration overlay"""
    
    # Find the latest simulation log
    log_files = glob.glob('/tmp/bio_nav_logs/nav_log_*.csv')
    if not log_files:
        print("No simulation logs found!")
        return
    
    latest_log = max(log_files, key=os.path.getctime)
    print(f"Loading data from: {latest_log}")
    
    # Load the data
    df = pd.read_csv(latest_log)
    
    # Extract position data
    x = df['x'].values
    y = df['y'].values
    gas_concentration = df['gas_concentration'].values
    timestamp = df['timestamp'].values
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create scatter plot with gas concentration as color
    scatter = ax.scatter(x, y, c=gas_concentration, cmap='viridis', 
                        s=20, alpha=0.6, edgecolors='none')
    
    # Plot the path as a line
    ax.plot(x, y, 'r-', alpha=0.3, linewidth=0.8, label='Robot Path')
    
    # Mark start and end points
    ax.scatter(x[0], y[0], c='green', s=200, marker='o', 
              label='Start', zorder=5, edgecolors='black', linewidth=2)
    ax.scatter(x[-1], y[-1], c='red', s=200, marker='s', 
              label='End', zorder=5, edgecolors='black', linewidth=2)
    
    # Mark gas source location (8.0, 8.0)
    ax.scatter(8.0, 8.0, c='orange', s=300, marker='*', 
              label='Gas Source', zorder=6, edgecolors='black', linewidth=2)
    
    # Add colorbar for gas concentration
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Gas Concentration', rotation=270, labelpad=15)
    
    ax.set_xlabel('X Position (m)')
    ax.set_ylabel('Y Position (m)')
    ax.set_title('Robot Trajectory with Gas Concentration Overlay')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Save the figure
    output_path = '/tmp/bio_nav_trajectory_2d.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Trajectory figure saved to: {output_path}")
    print(f"Total path length: {len(x)} points")
    print(f"Start: ({x[0]:.2f}, {y[0]:.2f})")
    print(f"End: ({x[-1]:.2f}, {y[-1]:.2f})")
    print(f"Gas source: (8.00, 8.00)")


if __name__ == '__main__':
    generate_trajectory_figure()