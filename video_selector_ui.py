"""
Video Selector UI - Web interface to choose the best take for each line
"""

from flask import Flask, render_template, request, jsonify, send_file
from pathlib import Path
import json
import re
import subprocess
from difflib import SequenceMatcher
import tempfile
import shutil
import threading

app = Flask(__name__)

# Global state
current_state = {
    'script_lines': [],
    'video_transcriptions': {},
    'matches_per_line': {},
    'selections': {},
    'trim_data': {},  # Store custom trim times {line_num: {start: float, end: float}}
    'processing': False,
    'video_folder': None,
    'transcription_folder': None,
}


def clean_text(text: str) -> str:
    """Clean and normalize text for matching."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()


def find_all_matches(script_line: str, video_transcriptions: dict, min_score: float = 0.5) -> list:
    """Find ALL videos that contain the script line."""
    matches = []
    script_line_clean = clean_text(script_line)
    
    if not script_line_clean:
        return matches
    
    for video_file, transcription in video_transcriptions.items():
        trans_clean = clean_text(transcription)
        
        # Check if line appears in transcription
        if script_line_clean in trans_clean:
            matches.append((video_file, 1.0, transcription[:100]))
            continue
        
        # Calculate similarity
        score = SequenceMatcher(None, script_line_clean, trans_clean).ratio()
        
        # Check for partial phrase matches
        line_words = script_line_clean.split()
        if len(line_words) >= 3:
            for window_size in range(min(len(line_words), 10), 2, -1):
                for i in range(len(line_words) - window_size + 1):
                    phrase = ' '.join(line_words[i:i + window_size])
                    if phrase in trans_clean:
                        phrase_score = 0.5 + (window_size / len(line_words)) * 0.5
                        if phrase_score > score:
                            score = phrase_score
        
        if score >= min_score:
            matches.append((video_file, score, transcription[:100]))
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def get_transcription_text(output_dir: str) -> str:
    """Extract text from transcription output."""
    txt_file = Path(output_dir) / "out.txt"
    if txt_file.exists():
        return txt_file.read_text()
    
    json_file = Path(output_dir) / "out.json"
    if json_file.exists():
        data = json.loads(json_file.read_text())
        if isinstance(data, dict) and "text" in data:
            return data["text"]
        elif isinstance(data, list):
            return " ".join([seg.get("text", "") for seg in data])
    
    return ""


def find_phrase_in_text(phrase: str, full_text: str) -> tuple:
    """Find where a phrase appears in text."""
    phrase_clean = clean_text(phrase)
    text_clean = clean_text(full_text)
    
    if not phrase_clean or not text_clean:
        return (0.0, 1.0)
    
    phrase_words = phrase_clean.split()
    text_words = text_clean.split()
    
    best_start = 0
    best_score = 0.0
    
    for i in range(len(text_words) - len(phrase_words) + 1):
        window = ' '.join(text_words[i:i + len(phrase_words)])
        score = SequenceMatcher(None, phrase_clean, window).ratio()
        if score > best_score:
            best_score = score
            best_start = i
    
    if best_score < 0.5:
        return (0.0, 1.0)
    
    best_end = best_start + len(phrase_words)
    start_ratio = best_start / len(text_words) if len(text_words) > 0 else 0.0
    end_ratio = best_end / len(text_words) if len(text_words) > 0 else 1.0
    
    return (start_ratio, end_ratio)


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
           '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, TypeError):
        return 0.0


def extract_video_segment(video_path: str, start_time: float, end_time: float, output_path: str):
    """Extract a segment from video with audio normalization."""
    duration = end_time - start_time
    
    # Use loudnorm filter to normalize audio levels to -16 LUFS (standard for video)
    cmd = [
        'ffmpeg', '-ss', str(start_time), '-i', str(video_path), '-t', str(duration),
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',  # Audio normalization
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-movflags', '+faststart', '-pix_fmt', 'yuv420p', '-y', str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)


def concatenate_videos(video_paths: list, output_path: str):
    """Concatenate multiple videos with proper sync (optimized for speed)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_path in video_paths:
            f.write(f"file '{Path(video_path).absolute()}'\n")
        list_file = f.name
    
    try:
        # Re-encode to fix sync issues - ensures constant framerate and timestamps
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            # Video encoding with constant framerate (fast preset for speed)
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-r', '24',  # Force constant 24fps
            '-vsync', 'cfr',  # Constant frame rate (critical for sync)
            # Audio normalization and encoding
            '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',  # Normalize overall audio
            '-c:a', 'aac',
            '-b:a', '192k',
            '-ar', '48000',  # Consistent sample rate
            '-async', '1',  # Audio sync correction
            # Output settings
            '-movflags', '+faststart',
            '-pix_fmt', 'yuv420p',
            '-y',
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    finally:
        Path(list_file).unlink()


def generate_final_video():
    """Generate the final video based on user selections."""
    current_state['processing'] = True
    
    try:
        temp_path = Path("temp_segments_ui")
        temp_path.mkdir(exist_ok=True)
        
        segment_paths = []
        selections = sorted(current_state['selections'].items(), key=lambda x: int(x[0]))
        
        for line_num_str, video_name in selections:
            line_num = int(line_num_str)
            script_line = current_state['script_lines'][line_num - 1]
            
            # Find the video file
            video_file = None
            for vf in current_state['video_transcriptions'].keys():
                if vf.name == video_name:
                    video_file = vf
                    break
            
            if not video_file:
                continue
            
            # Check if user has custom trim times
            trim_info = current_state['trim_data'].get(line_num_str)
            
            if trim_info and 'start' in trim_info and 'end' in trim_info:
                # Use custom trim times from user
                start_time = trim_info['start']
                end_time = trim_info['end']
            else:
                # Auto-detect timing from transcription
                trans_text = current_state['video_transcriptions'][video_file]
                start_ratio, end_ratio = find_phrase_in_text(script_line, trans_text)
                video_duration = get_video_duration(video_file)
                start_time = max(0, start_ratio * video_duration - 0.1)
                end_time = min(video_duration, end_ratio * video_duration + 0.1)
            
            # Extract segment
            segment_path = temp_path / f"segment_{line_num:03d}.mp4"
            extract_video_segment(video_file, start_time, end_time, segment_path)
            segment_paths.append(segment_path)
        
        # Concatenate
        output_path = "final_script_video_ui.mp4"
        concatenate_videos(segment_paths, output_path)
        
        # Cleanup
        shutil.rmtree(temp_path)
        
        current_state['processing'] = False
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        current_state['processing'] = False
        return False


@app.route('/')
def index():
    """Main page."""
    return render_template('selector.html')


@app.route('/api/initialize', methods=['POST'])
def initialize():
    """Initialize the selector with script and transcriptions."""
    
    # Read master script
    script_path = Path("master_script.txt")
    master_script = script_path.read_text()
    current_state['script_lines'] = [line.strip() for line in master_script.split('\n') if line.strip()]
    
    # Load transcriptions
    transcription_folder = Path("transcriptions")
    video_folder = Path("totranscribe")
    
    current_state['video_folder'] = video_folder
    current_state['transcription_folder'] = transcription_folder
    
    video_transcriptions = {}
    
    for trans_dir in transcription_folder.iterdir():
        if trans_dir.is_dir():
            trans_text = get_transcription_text(str(trans_dir))
            if trans_text:
                video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".MP4"]
                for ext in video_extensions:
                    video_path = video_folder / f"{trans_dir.name}{ext}"
                    if video_path.exists():
                        video_transcriptions[video_path] = trans_text
                        break
    
    current_state['video_transcriptions'] = video_transcriptions
    
    # Find matches for each line
    matches_per_line = {}
    for line_num, script_line in enumerate(current_state['script_lines'], 1):
        trans_dict = {vf.name: trans for vf, trans in video_transcriptions.items()}
        matches = find_all_matches(script_line, trans_dict, min_score=0.5)
        matches_per_line[line_num] = matches
    
    current_state['matches_per_line'] = matches_per_line
    
    return jsonify({
        'success': True,
        'total_lines': len(current_state['script_lines'])
    })


@app.route('/api/line/<int:line_num>')
def get_line_data(line_num):
    """Get data for a specific line."""
    if line_num < 1 or line_num > len(current_state['script_lines']):
        return jsonify({'error': 'Invalid line number'}), 400
    
    script_line = current_state['script_lines'][line_num - 1]
    matches = current_state['matches_per_line'].get(line_num, [])
    
    # Format matches for frontend
    match_data = []
    for video_name, score, preview in matches:
        # Get video path relative to web server
        match_data.append({
            'video_name': video_name,
            'score': score,
            'preview': preview,
            'video_url': f'/video/{video_name}'
        })
    
    return jsonify({
        'line_number': line_num,
        'script_line': script_line,
        'matches': match_data,
        'total_lines': len(current_state['script_lines']),
        'current_selection': current_state['selections'].get(str(line_num))
    })


@app.route('/video/<path:video_name>')
def serve_video(video_name):
    """Serve a video file."""
    video_path = current_state['video_folder'] / video_name
    if video_path.exists():
        return send_file(video_path, mimetype='video/mp4')
    return "Video not found", 404


@app.route('/api/select', methods=['POST'])
def select_take():
    """Record user's selection for a line."""
    data = request.json
    line_num = str(data.get('line_number'))
    video_name = data.get('video_name')
    trim = data.get('trim')  # {start: float, end: float}
    
    current_state['selections'][line_num] = video_name
    
    # Store trim data if provided
    if trim:
        current_state['trim_data'][line_num] = trim
    
    return jsonify({
        'success': True,
        'selections_count': len(current_state['selections'])
    })


@app.route('/api/generate', methods=['POST'])
def generate_video():
    """Generate the final video."""
    if current_state['processing']:
        return jsonify({'error': 'Already processing'}), 400
    
    # Run in background thread
    thread = threading.Thread(target=generate_final_video)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Video generation started'})


@app.route('/api/status')
def get_status():
    """Get current status."""
    return jsonify({
        'processing': current_state['processing'],
        'selections': current_state['selections'],
        'total_lines': len(current_state['script_lines'])
    })


@app.route('/api/save_session', methods=['POST'])
def save_session():
    """Save current selections and trim data to a file."""
    try:
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'session_{timestamp}.json'
        
        session_data = {
            'timestamp': timestamp,
            'selections': current_state['selections'],
            'trim_data': current_state['trim_data'],
            'total_lines': len(current_state['script_lines']),
            'selected_count': len(current_state['selections'])
        }
        
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
        
        return jsonify({
            'success': True,
            'filename': filename,
            'message': f'Session saved to {filename}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n🎬 Starting Video Selector UI...")
    print("📱 Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    app.run(debug=True, port=5000)

