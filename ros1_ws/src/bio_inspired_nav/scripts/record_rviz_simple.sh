#!/bin/bash
# Simple RViz Screen Recording Script
# Records the entire screen showing RViz

echo "=============================================="
echo "  📹 RViz Screen Recording (Simple Method)"
echo "=============================================="
echo ""

# Output directory
OUTPUT_DIR=~/Bio_Nav_RESULTS
mkdir -p "$OUTPUT_DIR"

# Video filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
VIDEO_FILE="$OUTPUT_DIR/rviz_3d_lidar_${TIMESTAMP}.mp4"

echo "📹 Recording Details:"
echo "   Output: $VIDEO_FILE"
echo ""
echo "⏱️  Recording Time:"
echo "   - Replay speed: 50x"
echo "   - 19 hours → ~23 minutes"
echo "   - Recording duration: 23 minutes"
echo ""
echo "🎬 Instructions:"
echo "   1. Make sure RViz window is visible"
echo "   2. Press ENTER to start 10-second countdown"
echo "   3. Arrange windows during countdown"
echo "   4. Recording starts automatically"
echo "   5. Press Ctrl+C to stop recording"
echo ""

read -p "Press ENTER when ready to start countdown..."

echo ""
echo "⏰ Starting in:"
for i in {10..1}; do
    echo "   $i..."
    sleep 1
done

echo ""
echo "🔴 RECORDING STARTED!"
echo "   Recording full screen..."
echo "   Press Ctrl+C to stop"
echo ""

# Get screen resolution
RESOLUTION=$(xdpyinfo | grep dimensions | awk '{print $2}')
echo "📺 Screen resolution: $RESOLUTION"
echo ""

# Record screen using ffmpeg
# -f x11grab: capture X11 screen
# -video_size: full screen
# -framerate 30: 30 FPS
# -i :0.0: display :0
ffmpeg -f x11grab -video_size "$RESOLUTION" -framerate 30 -i :0.0 \
    -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p \
    "$VIDEO_FILE" 2>&1 | grep --line-buffered -E "frame=|time=" &

FFMPEG_PID=$!

echo "Recording PID: $FFMPEG_PID"
echo ""

# Wait for user to stop
wait $FFMPEG_PID

echo ""
echo "✅ RECORDING COMPLETE!"
echo ""
echo "📊 Video Information:"
ls -lh "$VIDEO_FILE"
echo ""
echo "🎬 To view your video:"
echo "   vlc $VIDEO_FILE"
echo "   # or"
echo "   xdg-open $VIDEO_FILE"
echo ""
echo "=============================================="
