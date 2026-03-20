#!/usr/bin/env python3
"""
Generate Gas Concentration vs Time Figure
Shows gas_concentration over timestamp with peaks and plume detection events
"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import glob

def generate_gas_concentration_figure():
    """Generate gas concentration over time plot"""
    
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
    x = df['x'].values
    y = df['y'].values
    
    # Normalize timestamp to start from 0
    time_seconds = (timestamp - timestamp[0]) / 1e9  # Convert nanoseconds to seconds
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Plot gas concentration over time
    ax.plot(time_seconds, gas_concentration, 'b-', linewidth=1.0, alpha=0.8, label='Gas Concentration')
    
    # Highlight peaks (values above threshold)
    peak_threshold = np.percentile(gas_concentration, 90)  # Top 10% as peaks
    peak_indices = np.where(gas_concentration > peak_threshold)[0]
    
    if len(peak_indices) > 0:
        ax.scatter(time_seconds[peak_indices], gas_concentration[peak_indices], 
                  c='red', s=30, alpha=0.6, label=f'Peaks (> {peak_threshold:.1f})', zorder=5)
    
    # Add distance to source as secondary indicator
    distance_to_source = np.sqrt((x - 8.0)**2 + (y - 8.0)**2)
    ax2 = ax.twinx()
    ax2.plot(time_seconds, distance_to_source, 'g--', alpha=0.5, linewidth=1.0, label='Distance to Source')
    ax2.set_ylabel('Distance to Gas Source (m)', color='g')
    ax2.tick_params(axis='y', labelcolor='g')
    
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Gas Concentration', color='b')
    ax.set_title('Gas Concentration vs Time with Plume Detection Events')
    ax.grid(True, alpha=0.3)
    
    # Add legends
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    # Save the figure
    output_path = '/tmp/bio_nav_gas_concentration.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Gas concentration figure saved to: {output_path}")
    print(f"Total time: {time_seconds[-1]:.1f} seconds")
    print(f"Max concentration: {np.max(gas_concentration):.2f}")
    print(f"Mean concentration: {np.mean(gas_concentration):.2f}")
    print(f"Number of peaks detected: {len(peak_indices)}")


if __name__ == '__main__':
    generate_gas_concentration_figure()