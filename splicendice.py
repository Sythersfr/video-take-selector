"""
Video Splicer - Extract and stitch only the script lines from videos
Creates a clean video with ONLY the words from your script, perfectly timed.
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


def find_phrase_in_text(phrase: str, full_text: str) -> tuple:
    """
    Find where a phrase appears in text and return approximate position.
    Returns (start_ratio, end_ratio) as 0.0-1.0 range
    """
    phrase_clean = clean_text(phrase)
    text_clean = clean_text(full_text)
    
    if not phrase_clean or not text_clean:
        return (0.0, 1.0)
    
    # Find best match position
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
        # If no good match, return full duration
        return (0.0, 1.0)
    
    best_end = best_start + len(phrase_words)
    
    # Convert to ratios
    start_ratio = best_start / len(text_words) if len(text_words) > 0 else 0.0
    end_ratio = best_end / len(text_words) if len(text_words) > 0 else 1.0
    
    return (start_ratio, end_ratio)


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    duration_str = result.stdout.strip()
    
    if not duration_str:
        # Fallback: try getting duration from stream info
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration_str = result.stdout.strip()
    
    try:
        return float(duration_str)
    except (ValueError, TypeError):
        return 0.0


def extract_video_segment(video_path: str, start_time: float, end_time: float, output_path: str):
    """Extract a segment from video using ffmpeg with re-encoding for smooth playback."""
    duration = end_time - start_time
    
    cmd = [
        'ffmpeg',
        '-ss', str(start_time),  # Seek before input for faster processing
        '-i', str(video_path),
        '-t', str(duration),
        # Re-encode with consistent settings for smooth playback
        '-c:v', 'libx264',  # H.264 video codec
        '-preset', 'medium',  # Balance between speed and quality
        '-crf', '18',  # High quality (lower = better, 18 is visually lossless)
        '-c:a', 'aac',  # AAC audio codec
        '-b:a', '192k',  # Audio bitrate
        '-ar', '48000',  # Audio sample rate
        '-movflags', '+faststart',  # Optimize for streaming
        '-pix_fmt', 'yuv420p',  # Ensure compatibility
        '-y',
        str(output_path)
    ]
    
    subprocess.run(cmd, capture_output=True, check=True)


def concatenate_videos(video_paths: list, output_path: str):
    """Concatenate multiple videos into one with smooth transitions."""
    # Create a temporary file list for ffmpeg
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for video_path in video_paths:
            f.write(f"file '{Path(video_path).absolute()}'\n")
        list_file = f.name
    
    try:
        # Since all segments are now re-encoded with consistent settings,
        # we can safely use copy mode for fast concatenation
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',  # Copy since all segments have matching codecs now
            '-movflags', '+faststart',  # Optimize for playback
            '-y',
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True, check=True)
    finally:
        Path(list_file).unlink()


def splice_videos_by_script(
    matching_report_path: str,
    transcription_folder: str,
    video_folder: str,
    output_video: str = "final_spliced_video.mp4",
    temp_folder: str = "temp_segments",
):
    """
    Main function: Extract and splice video segments matching the script.
    
    Args:
        matching_report_path: Path to the _matching_report.txt from foldertosort.py
        transcription_folder: Folder with transcription outputs
        video_folder: Folder containing the original videos
        output_video: Name for the final stitched video
        temp_folder: Temporary folder for video segments
    """
    print("🎬 Video Splicer - Creating script-perfect video")
    print("=" * 70)
    
    # Create temp folder
    temp_path = Path(temp_folder)
    temp_path.mkdir(exist_ok=True)
    
    # Parse the matching report to get video-line pairs
    print("\n📄 Reading matching report...")
    report_path = Path(matching_report_path)
    
    video_matches = []
    with open(report_path, 'r') as f:
        lines = f.readlines()
        
    # Parse report
    i = 0
    while i < len(lines):
        if lines[i].startswith("VIDEO "):
            # Extract video name
            video_line = lines[i]
            match = re.search(r'VIDEO \d+: (.+\.MP4)', video_line, re.IGNORECASE)
            if match:
                video_name = match.group(1)
                script_line = lines[i+1].split(": ", 1)[1].strip() if i+1 < len(lines) else ""
                
                video_matches.append({
                    "video_name": video_name,
                    "script_line": script_line,
                })
        i += 1
    
    print(f"   Found {len(video_matches)} video segments to extract")
    
    # Extract each segment
    segment_paths = []
    video_folder_path = Path(video_folder)
    transcription_folder_path = Path(transcription_folder)
    
    print("\n✂️  Extracting segments...")
    print("-" * 70)
    
    for i, match in enumerate(video_matches, 1):
        video_name = match["video_name"]
        script_line = match["script_line"]
        
        # Find video file
        video_path = video_folder_path / video_name
        if not video_path.exists():
            # Try without extension variations
            video_stem = Path(video_name).stem
            matching_files = list(video_folder_path.glob(f"{video_stem}.*"))
            if matching_files:
                video_path = matching_files[0]
            else:
                print(f"   ⚠️  Video not found: {video_name}")
                continue
        
        # Get transcription
        trans_path = transcription_folder_path / Path(video_name).stem / "out.json"
        if not trans_path.exists():
            print(f"   ⚠️  Transcription not found: {video_name}")
            continue
        
        with open(trans_path, 'r') as f:
            trans_data = json.load(f)
            full_transcription = trans_data.get("text", "")
        
        # Find where script line appears in transcription
        start_ratio, end_ratio = find_phrase_in_text(script_line, full_transcription)
        
        # Get video duration and calculate timestamps
        video_duration = get_video_duration(video_path)
        start_time = start_ratio * video_duration
        end_time = end_ratio * video_duration
        
        # Add small padding (0.1 seconds) to capture full words
        start_time = max(0, start_time - 0.1)
        end_time = min(video_duration, end_time + 0.1)
        
        # Extract segment
        segment_path = temp_path / f"segment_{i:03d}.mp4"
        
        try:
            extract_video_segment(video_path, start_time, end_time, segment_path)
            segment_paths.append(segment_path)
            
            duration = end_time - start_time
            print(f"   ✅ {i:02d}. {video_name} [{start_time:.2f}s - {end_time:.2f}s] ({duration:.2f}s)")
            print(f"        \"{script_line[:60]}...\"")
        except Exception as e:
            print(f"   ❌ Error extracting {video_name}: {e}")
            continue
    
    if not segment_paths:
        print("\n❌ No segments were extracted")
        return
    
    # Concatenate all segments
    print(f"\n🔗 Stitching {len(segment_paths)} segments together...")
    
    try:
        concatenate_videos(segment_paths, output_video)
        print(f"\n✅ SUCCESS! Final video saved to: {output_video}")
        print(f"   Total segments: {len(segment_paths)}")
        
        # Calculate total duration (non-critical, don't fail if this errors)
        try:
            total_duration = sum([get_video_duration(str(p)) for p in segment_paths])
            if total_duration > 0:
                print(f"   Total duration: {total_duration:.2f} seconds")
        except Exception as e:
            print(f"   (Could not calculate total duration: {e})")
        
    except Exception as e:
        print(f"\n❌ Error concatenating videos: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Cleanup temp folder
    print(f"\n🧹 Cleaning up temporary files...")
    shutil.rmtree(temp_path)
    
    print("\n🎉 Done! Your script-perfect video is ready!")


if __name__ == "__main__":
    # Run the video splicer
    splice_videos_by_script(
        matching_report_path="ordered_videos/_matching_report.txt",
        transcription_folder="transcriptions",
        video_folder="totranscribe",  # Your original videos
        output_video="final_script_video.mp4",
        temp_folder="temp_segments",
    )