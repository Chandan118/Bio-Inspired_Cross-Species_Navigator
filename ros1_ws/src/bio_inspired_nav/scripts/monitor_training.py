#!/usr/bin/env python3
"""
Training Progress Monitor
Real-time monitoring and visualization of training progress
"""

import os
import json
import csv
import time
from datetime import datetime, timedelta

class TrainingMonitor:
    """Monitor and display training progress"""
    
    def __init__(self, results_dir='/tmp/bio_nav_training_results'):
        self.results_dir = results_dir
        self.progress_file = os.path.join(results_dir, 'progress.json')
    
    def get_progress(self):
        """Get current training progress"""
        if not os.path.exists(self.progress_file):
            return None
        
        try:
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        except:
            return None
    
    def get_latest_results(self, n=10):
        """Get latest N episode results"""
        csv_files = [f for f in os.listdir(self.results_dir) 
                     if f.startswith('training_results') and f.endswith('.csv')]
        
        if not csv_files:
            return []
        
        latest_csv = sorted(csv_files)[-1]
        csv_path = os.path.join(self.results_dir, latest_csv)
        
        results = []
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                results.append(row)
        
        return results[-n:]
    
    def display_progress(self):
        """Display current training progress"""
        progress = self.get_progress()
        
        if not progress:
            print("No training in progress")
            return
        
        current_ep = progress.get('current_episode', 0)
        target_ep = 4500  # Default
        
        # Calculate progress
        progress_pct = (current_ep / target_ep) * 100 if target_ep > 0 else 0
        
        # Calculate time estimates
        elapsed_time = progress.get('elapsed_time', 0)
        if current_ep > 0:
            time_per_episode = elapsed_time / current_ep
            remaining_episodes = target_ep - current_ep
            est_remaining_time = time_per_episode * remaining_episodes
        else:
            time_per_episode = 0
            est_remaining_time = 0
        
        # Display
        print("\n" + "="*60)
        print("TRAINING PROGRESS")
        print("="*60)
        print(f"Episodes: {current_ep}/{target_ep} ({progress_pct:.1f}%)")
        print(f"Progress: [{'#'*int(progress_pct/2)}{'-'*int(50-progress_pct/2)}]")
        print(f"\nTime:")
        print(f"  Elapsed: {timedelta(seconds=int(elapsed_time))}")
        print(f"  Remaining: {timedelta(seconds=int(est_remaining_time))}")
        print(f"  Per Episode: {time_per_episode:.1f}s")
        print(f"\nLast Update: {progress.get('timestamp', 'N/A')}")
        print("="*60)
        
        # Show recent results
        recent = self.get_latest_results(5)
        if recent:
            print("\nRecent Episodes:")
            print("-"*60)
            for r in recent:
                print(f"  Ep {r['episode']}: "
                      f"Duration={r['duration_sec']}s, "
                      f"Distance={r['distance_traveled']}m, "
                      f"Success={r['success']}")
            print("-"*60)
        
        print("\n")
    
    def monitor_loop(self, interval=30):
        """Continuously monitor and display progress"""
        print("Training Monitor Started")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                os.system('clear' if os.name != 'nt' else 'cls')
                self.display_progress()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nMonitor stopped")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Training Progress Monitor')
    parser.add_argument('--interval', type=int, default=30,
                       help='Update interval in seconds (default: 30)')
    parser.add_argument('--once', action='store_true',
                       help='Show progress once and exit')
    
    args = parser.parse_args()
    
    monitor = TrainingMonitor()
    
    if args.once:
        monitor.display_progress()
    else:
        monitor.monitor_loop(args.interval)


if __name__ == '__main__':
    main()
