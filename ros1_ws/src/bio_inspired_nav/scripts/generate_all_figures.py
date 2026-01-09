#!/usr/bin/env python3
"""
Generate All 6 Key Figures for SUPPLEMENTARY MATERIAL
"""
import subprocess
import sys
import os

def generate_all_figures():
    """Generate all 6 requested figures"""
    
    print("="*60)
    print("GENERATING 6 KEY FIGURES FOR SUPPLEMENTARY MATERIAL")
    print("="*60)
    
    # List of figure generation scripts
    scripts = [
        ("1. Robot Trajectory", "figure_trajectory.py"),
        ("2. Gas Concentration vs Time", "figure_gas_concentration.py"),
        ("3. Distance to Source Over Time", "figure_distance_to_source.py"),
        ("4. Navigation State Transitions", "figure_state_transitions.py"),
        ("5. Velocity Profiles", "figure_velocity_profiles.py"),
        ("6. Gas Gradient vs Robot Heading", "figure_gas_gradient_heading.py")
    ]
    
    success_count = 0
    total_count = len(scripts)
    
    for name, script in scripts:
        print(f"\n{name}:")
        print("-" * 40)
        
        try:
            # Run the script
            result = subprocess.run([
                sys.executable, 
                f"src/bio_inspired_nav/scripts/{script}"
            ], cwd="/home/chandan/Bio-Inspired_Cross-Species_Navigator/ros1_ws", 
               capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"✅ {name} - SUCCESS")
                # Print the output
                if result.stdout:
                    print(result.stdout.strip())
                success_count += 1
            else:
                print(f"❌ {name} - FAILED")
                if result.stderr:
                    print(f"Error: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            print(f"❌ {name} - TIMEOUT (30 seconds)")
        except Exception as e:
            print(f"❌ {name} - ERROR: {str(e)}")
    
    print("\n" + "="*60)
    print("FIGURE GENERATION SUMMARY")
    print("="*60)
    print(f"Successfully generated: {success_count}/{total_count} figures")
    
    if success_count == total_count:
        print("🎉 All figures generated successfully!")
        print("\nGenerated figures are located at:")
        print("  /tmp/bio_nav_trajectory_2d.png")
        print("  /tmp/bio_nav_gas_concentration.png")
        print("  /tmp/bio_nav_distance_to_source.png")
        print("  /tmp/bio_nav_state_transitions.png")
        print("  /tmp/bio_nav_velocity_profiles.png")
        print("  /tmp/bio_nav_gas_gradient_heading.png")
    else:
        print(f"⚠️  {total_count - success_count} figures failed to generate")
    
    print("="*60)

if __name__ == '__main__':
    generate_all_figures()