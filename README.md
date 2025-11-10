# 🎬 Video Take Selector & Script Matcher

A powerful video editing suite that automatically transcribes video clips, matches them to your script, and lets you select the perfect take with a beautiful web interface.

## ✨ Features

### 🎯 **Smart Script Matching**
- Automatically finds ALL clips that match each line of your script
- Confidence scoring (Excellent, Good, Fair)
- Matches even with slight variations in dialogue

### 📺 **Beautiful Web Interface**
- Modern, gradient-based UI
- Video previews for each take
- Side-by-side comparison of all options
- Progress tracking

### ✂️ **Precision Video Trimming**
- Drag-and-drop trim markers
- Real-time audio waveform visualization
- Precise timing to 0.01 seconds
- Visual preview as you trim

### 🎵 **Audio Waveform**
- Beautiful gradient waveform visualization
- See audio levels across the entire clip
- Perfect for finding dialogue start/end points

### ⚡ **Fast Processing**
- Apple Silicon MLX acceleration for M-series Macs
- Batch transcription of multiple videos
- Re-encoding with smooth playback

## 🚀 Quick Start

### Prerequisites
```bash
# Install Python dependencies
pip3 install Flask transcribe-anything

# Install ffmpeg (if not already installed)
brew install ffmpeg
```

### Run the Web UI

1. **Place your videos** in the `totranscribe/` folder
2. **Create your script** in `master_script.txt` (one line per take)
3. **Start the web server:**
   ```bash
   python3 video_selector_ui.py
   ```
4. **Open your browser** to http://localhost:5000

### Usage Flow

1. **Transcription** - Videos are auto-transcribed (happens once)
2. **Matching** - Each script line is matched to video clips
3. **Selection** - Choose the best take for each line
4. **Trimming** - Fine-tune start/end points with waveform
5. **Generation** - Create final video with selected takes

## 📁 Project Structure

```
.
├── video_selector_ui.py        # Main web application
├── templates/
│   └── selector.html           # Web interface
├── foldertosort.py             # Batch script matching
├── foldertranscribe.py         # Batch transcription
├── splicendice.py              # Video splicing
├── interactive_splicer.py      # Command-line interactive version
├── master_script.txt           # Your script (one line per take)
├── totranscribe/               # Input: place videos here
├── transcriptions/             # Auto-generated transcriptions
└── ordered_videos/             # Output: matched & ordered videos
```

## 🎨 Web Interface Features

### Video Cards
- Click any video to select it
- Selected cards show blue border
- Trim controls appear only on selected card

### Trim Controls (Selected Cards Only)
- **Waveform Bar** - Visual audio representation
- **Timeline** - Drag markers to trim
- **Time Display** - Start, Duration, End times
- Real-time video preview as you drag

### Navigation
- **Previous** - Go back a line
- **Skip** - Skip current line
- **Next** - Move to next line
- **Finish Now** - Generate video with current selections

## 🛠️ Alternative Scripts

### Command Line Transcription
```bash
python3 foldertranscribe.py
```

### Automatic Matching & Organization
```bash
python3 foldertosort.py
```

### Manual Splicing
```bash
python3 splicendice.py
```

## 📝 Script Format

Your `master_script.txt` should have one line per dialogue/take:

```text
Why are you lying to me?
I'm not lying to you.
But you're not telling me everything.
Since when do I have to?
```

## 🎯 Tips

- **Higher confidence = better match** - Look for ✅ green badges
- **Preview videos** - Play before selecting
- **Use waveform** - Find exact dialogue start/end
- **Trim precisely** - Drag markers while watching waveform
- **Skip uncertain lines** - Come back later
- **Finish early** - Generate with partial selections for preview

## 🔧 Technical Details

### Transcription
- Uses `transcribe-anything` with Apple MLX backend
- Whisper large-v3 model for accuracy
- Results cached in `transcriptions/` folder

### Video Processing
- H.264 encoding with CRF 18 (near-lossless)
- AAC audio at 192k
- Optimized for smooth playback
- No re-encoding of untrimmed segments

### Matching Algorithm
- SequenceMatcher for fuzzy matching
- Sliding window phrase detection
- Confidence scoring based on match quality

## 🎬 Output

Final videos are saved as:
- **Web UI**: `final_script_video_ui.mp4`
- **Auto Script**: `final_script_video.mp4`

## 🐛 Troubleshooting

**Port already in use?**
```bash
# Kill existing process
lsof -ti:5000 | xargs kill
```

**Videos not loading?**
- Ensure videos are in `totranscribe/` folder
- Check video format (MP4, MOV, AVI supported)

**Flask not installed?**
```bash
pip3 install Flask
```

**Transcription slow?**
- Use smaller model: `model="base"` in the script
- Reduce batch size
- First run downloads model (~3GB)

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Credits

Built with:
- Flask for web interface
- transcribe-anything for audio transcription
- ffmpeg for video processing
- Canvas API for waveform visualization

---

Made with ❤️ for filmmakers and video editors

