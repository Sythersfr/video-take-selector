# 🎬 Video Take Selector UI

## Beautiful web interface to choose the best take for each line!

### Quick Start

**Option 1: Using the startup script (easiest)**
```bash
cd "/Users/nicp/Documents/min vibes"
chmod +x start_ui.sh
./start_ui.sh
```

**Option 2: Manual start**
```bash
cd "/Users/nicp/Documents/min vibes"
pip3 install Flask
python3 video_selector_ui.py
```

Then open your browser to: **http://localhost:5000**

---

## Features ✨

### 📺 **Video Previews**
- Watch each take directly in the browser
- See all available options side-by-side
- Video player with full controls

### 🎯 **Smart Matching**
- Automatically finds ALL videos that match each script line
- Color-coded confidence scores:
  - ✅ **Green (Excellent)**: 80%+ match
  - ⚠️ **Yellow (Good)**: 60-80% match
  - ❓ **Red (Fair)**: 50-60% match

### 🎨 **Beautiful Interface**
- Modern, gradient design
- Responsive grid layout
- Progress bar showing completion
- Smooth animations

### ⚡ **Easy Navigation**
- Click any video to select it
- Use Next/Previous buttons to navigate
- Progress automatically saved
- Generate final video when all lines are selected

---

## How It Works

1. **Script is Loaded**
   - Reads your `master_script.txt`
   - Loads all transcriptions from the `transcriptions/` folder

2. **For Each Line:**
   - Shows the script line at the top
   - Displays all matching video takes in a grid
   - Each video shows:
     - Video preview player
     - Filename
     - Confidence score
     - Text preview

3. **Selection:**
   - Click on any video card to select it
   - Selected card gets highlighted with blue border
   - Navigate between lines with Next/Previous buttons

4. **Generation:**
   - Once all lines are selected, "Generate Final Video" button appears
   - Click to start processing
   - Video segments are extracted and stitched together
   - Final video saved as `final_script_video_ui.mp4`

---

## Tips 💡

- **Play videos before selecting** - Click the play button to watch each take
- **Check confidence scores** - Higher scores usually mean better matches
- **Read the preview text** - See what words are actually in each video
- **You can change selections** - Go back to any line and click a different video
- **Progress is saved** - Your selections are remembered as you navigate

---

## Troubleshooting

**Port already in use?**
- Stop the previous instance with Ctrl+C
- Or change the port in `video_selector_ui.py` (last line: `app.run(port=5000)`)

**Videos not playing?**
- Make sure videos are in the `totranscribe/` folder
- Try refreshing the page

**Flask not installed?**
```bash
pip3 install Flask
```

---

## Output

Your custom video will be saved as:
**`final_script_video_ui.mp4`**

Enjoy creating your perfect video! 🎉

