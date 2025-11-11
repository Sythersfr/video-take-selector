"""
Interactive Video Splicer - Choose the best take for each line
Finds ALL instances of each script line and lets you pick which one to use.
"""

from pathlib import Path
import json
import re
import subprocess
from difflib import SequenceMatcher
import tempfile
import shutil


def clean_text(text: str) -> str:
    """Clean and normalize text for matching."""
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)
    return text.strip()


def find_all_matches(script_line: str, video_transcriptions: dict, min_score: float = 0.6) -> list:
    """
    Find ALL videos that contain the script line.
    Returns list of (video_file, score, matched_text) sorted by score.
    """
    matches = []
    script_line_clean = clean_text(script_line)
    
    if not script_line_clean:
        return matches
    
    for video_file, transcription in video_transcriptions.items():
        trans_clean = clean_text(transcription)
        
        # Check if line appears in transcription
        if script_line_clean in trans_clean:
            matches.append((video_file, 1.0, script_line))
            continue
        
        # Calculate similarity
        score = SequenceMatcher(None, script_line_clean, trans_clean).ratio()
        
        # Also check for partial phrase matches
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
            matches.append((video_file, score, transcription[:80]))
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def find_phrase_in_text(phrase: str, full_text: str) -> tuple:
    """Find where a phrase appears in text and return approximate position."""
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
    """Concatenate multiple videos with perfect audio/video sync (optimized for speed)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_path in video_paths:
            f.write(f"file '{Path(video_path).absolute()}'\n")
        list_file = f.name
    
    try:
        # Re-encode to prevent audio drift and sync issues
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            # Video encoding with constant framerate (fast preset)
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', '23',
            '-r', '24',  # Force constant 24fps
            '-vsync', 'cfr',  # Constant frame rate (fixes drift)
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


def interactive_splice_videos(
    transcription_folder: str,
    video_folder: str,
    master_script_file: str,
    output_video: str = "final_script_video.mp4",
    temp_folder: str = "temp_segments",
):
    """
    Interactive video splicer - choose the best take for each line.
    """
    print("\n🎬 Interactive Video Splicer")
    print("=" * 70)
    
    # Read master script
    print("\n📜 Reading master script...")
    master_script = Path(master_script_file).read_text()
    script_lines = [line.strip() for line in master_script.split('\n') if line.strip()]
    print(f"   Found {len(script_lines)} lines in script")
    
    # Load all transcriptions
    print("\n📂 Loading transcriptions...")
    transcription_folder_path = Path(transcription_folder)
    video_folder_path = Path(video_folder)
    
    video_transcriptions = {}
    
    for trans_dir in transcription_folder_path.iterdir():
        if trans_dir.is_dir():
            trans_text = get_transcription_text(str(trans_dir))
            if trans_text:
                # Find corresponding video file
                video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"]
                for ext in video_extensions:
                    video_path = video_folder_path / f"{trans_dir.name}{ext}"
                    if video_path.exists():
                        video_transcriptions[video_path] = trans_text
                        break
    
    print(f"   Loaded {len(video_transcriptions)} video transcriptions")
    
    # For each script line, find all matches and let user choose
    print("\n" + "=" * 70)
    print("🎯 SELECTING TAKES FOR EACH LINE")
    print("=" * 70)
    
    user_selections = []  # [(line_number, video_file, script_line)]
    
    for line_num, script_line in enumerate(script_lines, 1):
        print(f"\n📝 Line {line_num}/{len(script_lines)}: \"{script_line}\"")
        print("-" * 70)
        
        # Find all matching videos
        trans_dict = {vf.name: trans for vf, trans in video_transcriptions.items()}
        matches = find_all_matches(script_line, trans_dict, min_score=0.5)
        
        if not matches:
            print("   ❌ No matches found for this line!")
            continue
        
        # Show all options
        print(f"   Found {len(matches)} possible take(s):\n")
        for i, (video_name, score, preview) in enumerate(matches, 1):
            confidence_icon = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❓"
            print(f"   {i}. {confidence_icon} {video_name} (confidence: {score:.0%})")
            print(f"      Preview: {preview}...\n")
        
        # Ask user to choose
        while True:
            try:
                choice = input(f"   Choose take 1-{len(matches)} (or 's' to skip, 'q' to quit): ").strip().lower()
                
                if choice == 'q':
                    print("\n⚠️  Quitting...")
                    return
                elif choice == 's':
                    print("   ⏩ Skipping this line\n")
                    break
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(matches):
                    selected_video_name = matches[choice_num - 1][0]
                    # Find the actual video file object
                    selected_video = next(vf for vf in video_transcriptions.keys() 
                                         if vf.name == selected_video_name)
                    
                    user_selections.append({
                        'line_number': line_num,
                        'script_line': script_line,
                        'video_file': selected_video,
                        'score': matches[choice_num - 1][1],
                    })
                    print(f"   ✅ Selected: {selected_video_name}\n")
                    break
                else:
                    print(f"   Please enter a number between 1 and {len(matches)}")
            except ValueError:
                print(f"   Please enter a valid number, 's', or 'q'")
    
    if not user_selections:
        print("\n❌ No selections made. Exiting.")
        return
    
    # Extract and stitch selected segments
    print("\n" + "=" * 70)
    print(f"✂️  EXTRACTING {len(user_selections)} SELECTED SEGMENTS")
    print("=" * 70)
    
    temp_path = Path(temp_folder)
    temp_path.mkdir(exist_ok=True)
    
    segment_paths = []
    
    for i, selection in enumerate(user_selections, 1):
        video_file = selection['video_file']
        script_line = selection['script_line']
        
        print(f"\n{i:02d}. {video_file.name}: \"{script_line[:50]}...\"")
        
        # Get transcription
        trans_text = video_transcriptions[video_file]
        
        # Find timing
        start_ratio, end_ratio = find_phrase_in_text(script_line, trans_text)
        video_duration = get_video_duration(video_file)
        start_time = max(0, start_ratio * video_duration - 0.1)
        end_time = min(video_duration, end_ratio * video_duration + 0.1)
        
        # Extract segment
        segment_path = temp_path / f"segment_{i:03d}.mp4"
        
        try:
            extract_video_segment(video_file, start_time, end_time, segment_path)
            segment_paths.append(segment_path)
            print(f"    ✅ Extracted [{start_time:.2f}s - {end_time:.2f}s]")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    # Concatenate
    print(f"\n🔗 Stitching {len(segment_paths)} segments together...")
    
    try:
        concatenate_videos(segment_paths, output_video)
        print(f"\n✅ SUCCESS! Video saved to: {output_video}")
        print(f"   Total segments: {len(segment_paths)}")
    except Exception as e:
        print(f"\n❌ Error concatenating: {e}")
        return
    
    # Cleanup
    print(f"\n🧹 Cleaning up...")
    shutil.rmtree(temp_path)
    
    print("\n🎉 Done! Your custom video is ready!")


if __name__ == "__main__":
    interactive_splice_videos(
        transcription_folder="transcriptions",
        video_folder="totranscribe",
        master_script_file="master_script.txt",
        output_video="final_script_video_interactive.mp4",
        temp_folder="temp_segments_interactive",
    )

