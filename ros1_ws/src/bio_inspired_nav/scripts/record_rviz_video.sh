#!/bin/bash
# Record RViz Visualization Video
# This script records the RViz window as a video

echo "=============================================="
echo "  RViz Video Recording Script"
echo "=============================================="
echo ""

# Output directory
OUTPUT_DIR=~/Bio_Nav_RESULTS
mkdir -p "$OUTPUT_DIR"

# Video filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
VIDEO_FILE="$OUTPUT_DIR/rviz_replay_${TIMESTAMP}.mp4"

echo "📹 Recording will be saved to:"
echo "   $VIDEO_FILE"
echo ""
echo "⏱️  Estimated recording time: ~12 minutes"
echo "   (replaying 19 hours at 100x speed)"
echo ""
echo "🎬 Instructions:"
echo "   1. Position RViz window where you want it"
echo "   2. Press ENTER to start recording"
echo "   3. Replay will start automatically"
echo "   4. Recording stops when replay completes"
echo ""

read -p "Press ENTER when ready to start..."

echo ""
echo "🔴 RECORDING STARTED!"
echo "   Recording RViz window for ~12 minutes..."
echo ""

# Find RViz window ID
WINDOW_ID=$(xdotool search --name "RViz" | head -1)

if [ -z "$WINDOW_ID" ]; then
    echo "❌ Error: RViz window not found!"
    echo "   Please start RViz first"
    exit 1
fi

# Get window geometry
eval $(xdotool getwindowgeometry --shell $WINDOW_ID)

# Record using ffmpeg (captures specific window)
ffmpeg -f x11grab -video_size ${WIDTH}x${HEIGHT} -i :0.0+${X},${Y} \
    -framerate 30 -t 720 -c:v libx264 -preset fast -crf 23 \
    "$VIDEO_FILE" &

FFMPEG_PID=$!

echo "Recording PID: $FFMPEG_PID"
echo ""
echo "⏳ Recording in progress..."
echo "   - Wait for replay to complete (~12 min)"
echo "   - Or press Ctrl+C to stop early"
echo ""

# Wait for recording to finish
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
