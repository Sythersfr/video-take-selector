"""
Video Script Matcher and Organizer
- Transcribes all videos in a folder
- Matches transcriptions to a master script
- Renames and copies videos in script order
"""

from transcribe_anything import transcribe
from pathlib import Path
import shutil
import json
from difflib import SequenceMatcher
import re


def run_mac_transcription(
    source: str,
    output_dir: str = "output",
    model: str = "large-v3",
    batch_size: int = 12,
):
    """Transcribe a video file using Apple MLX."""
    print(f"🎧 Transcribing: {Path(source).name}")
    
    output_path = transcribe(
        url_or_file=source,
        output_dir=output_dir,
        model=model,
        device="mlx",
        other_args=["--batch_size", str(batch_size)],
    )
    
    return output_path


def get_transcription_text(output_dir: str) -> str:
    """Extract text from transcription output."""
    # Try to read the .txt file first
    txt_file = Path(output_dir) / "out.txt"
    if txt_file.exists():
        return txt_file.read_text()
    
    # Fallback to JSON if txt doesn't exist
    json_file = Path(output_dir) / "out.json"
    if json_file.exists():
        data = json.loads(json_file.read_text())
        if isinstance(data, dict) and "text" in data:
            return data["text"]
        elif isinstance(data, list):
            return " ".join([seg.get("text", "") for seg in data])
    
    return ""


def clean_text(text: str) -> str:
    """Clean and normalize text for matching."""
    # Convert to lowercase, remove extra whitespace
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text.strip()


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculate similarity between two text strings."""
    clean1 = clean_text(text1)
    clean2 = clean_text(text2)
    
    if not clean1 or not clean2:
        return 0.0
    
    return SequenceMatcher(None, clean1, clean2).ratio()


def find_best_video_for_line(script_line: str, video_transcriptions: dict) -> tuple:
    """
    Find which video best matches a specific line from the script.
    Returns (video_name, best_score, matched_portion)
    """
    best_video = None
    best_score = 0.0
    best_match = ""
    
    script_line_clean = clean_text(script_line)
    if not script_line_clean:
        return (None, 0.0, "")
    
    for video_name, transcription in video_transcriptions.items():
        trans_clean = clean_text(transcription)
        
        # Try exact line match first
        if script_line_clean in trans_clean:
            return (video_name, 1.0, script_line)
        
        # Calculate overall similarity
        score = SequenceMatcher(None, script_line_clean, trans_clean).ratio()
        
        # Also check if any substantial portion of the line appears
        line_words = script_line_clean.split()
        if len(line_words) >= 3:
            # Check for phrase matches (sliding window)
            for window_size in range(min(len(line_words), 10), 2, -1):
                for i in range(len(line_words) - window_size + 1):
                    phrase = ' '.join(line_words[i:i + window_size])
                    if phrase in trans_clean:
                        # Boost score for partial matches
                        phrase_score = 0.5 + (window_size / len(line_words)) * 0.5
                        if phrase_score > score:
                            score = phrase_score
                            best_match = phrase
        
        if score > best_score:
            best_score = score
            best_video = video_name
            if not best_match:
                best_match = transcription[:100]
    
    return (best_video, best_score, best_match)


def transcribe_and_match_videos(
    video_folder: str,
    master_script_file: str,
    output_folder: str = "ordered_videos",
    transcription_folder: str = "transcriptions",
    model: str = "large-v3",
    batch_size: int = 12,
    min_confidence: float = 0.3,
):
    """
    Main function: Transcribe videos, match line-by-line to script, and organize them.
    
    Args:
        video_folder: Folder containing unordered video files
        master_script_file: Path to your pre-written script (.txt file)
        output_folder: Where to save renamed/ordered videos
        transcription_folder: Where to save transcription outputs
        model: Whisper model to use
        batch_size: Batch size for transcription
        min_confidence: Minimum matching confidence (0-1)
    """
    video_folder_path = Path(video_folder)
    output_folder_path = Path(output_folder)
    transcription_folder_path = Path(transcription_folder)
    
    # Create output directories
    output_folder_path.mkdir(exist_ok=True)
    transcription_folder_path.mkdir(exist_ok=True)
    
    # Read master script
    print("\n📜 Reading master script...")
    master_script = Path(master_script_file).read_text()
    script_lines = [line.strip() for line in master_script.split('\n') if line.strip()]
    print(f"   Script has {len(script_lines)} lines")
    
    # Find all video files
    video_extensions = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v")
    video_files = [f for f in video_folder_path.iterdir() if f.suffix.lower() in video_extensions]
    
    if not video_files:
        print(f"❌ No video files found in {video_folder}")
        return
    
    print(f"\n📂 Found {len(video_files)} video(s) to transcribe")
    print("=" * 70)
    
    # Step 1: Transcribe all videos and store transcriptions
    video_transcriptions = {}  # {video_file: transcription_text}
    
    for i, video_file in enumerate(video_files, 1):
        print(f"\n🎬 [{i}/{len(video_files)}] Transcribing: {video_file.name}")
        print("-" * 70)
        
        trans_output_dir = transcription_folder_path / video_file.stem
        
        try:
            # Check if already transcribed
            if trans_output_dir.exists():
                print(f"   ⏩ Using existing transcription")
                trans_text = get_transcription_text(str(trans_output_dir))
            else:
                # Transcribe video
                run_mac_transcription(
                    source=str(video_file),
                    output_dir=str(trans_output_dir),
                    model=model,
                    batch_size=batch_size,
                )
                trans_text = get_transcription_text(str(trans_output_dir))
            
            if not trans_text:
                print(f"⚠️  Warning: No transcription text found for {video_file.name}")
                continue
            
            video_transcriptions[video_file] = trans_text
            print(f"   ✅ Transcribed: {trans_text[:80]}...")
                
        except Exception as e:
            print(f"❌ Error processing {video_file.name}: {e}")
            continue
    
    if not video_transcriptions:
        print("\n❌ No videos were successfully transcribed")
        return
    
    # Step 2: Match each script line to the best video
    print("\n" + "=" * 70)
    print("🔍 MATCHING SCRIPT LINES TO VIDEOS")
    print("=" * 70)
    
    line_matches = []  # [(line_number, video_file, score, matched_text)]
    
    for line_num, script_line in enumerate(script_lines, 1):
        print(f"\n📝 Line {line_num}/{len(script_lines)}: \"{script_line[:60]}...\"")
        
        # Convert video files to simple dict for matching
        trans_dict = {vf.name: trans for vf, trans in video_transcriptions.items()}
        
        best_video_name, score, matched_text = find_best_video_for_line(script_line, trans_dict)
        
        if best_video_name:
            # Find the actual video file object
            best_video_file = next(vf for vf in video_transcriptions.keys() if vf.name == best_video_name)
            
            confidence_icon = "✅" if score >= min_confidence else "⚠️"
            print(f"   {confidence_icon} Best match: {best_video_name} (confidence: {score:.2%})")
            print(f"      Matched: {matched_text[:60]}...")
            
            line_matches.append({
                "line_number": line_num,
                "script_line": script_line,
                "video_file": best_video_file,
                "score": score,
                "matched_text": matched_text,
            })
        else:
            print(f"   ❌ No match found")
    
    if not line_matches:
        print("\n❌ No matches found between script and videos")
        return
    
    # Step 3: Order videos by script line order
    print("\n" + "=" * 70)
    print("📊 ORGANIZING VIDEOS BY SCRIPT ORDER")
    print("=" * 70)
    
    # Sort by line number
    line_matches.sort(key=lambda x: x["line_number"])
    
    # Remove duplicates - keep only first occurrence of each video
    seen_videos = set()
    unique_matches = []
    for match in line_matches:
        if match["video_file"] not in seen_videos:
            seen_videos.add(match["video_file"])
            unique_matches.append(match)
    
    # Step 4: Copy and rename videos in order
    print(f"\n📁 Creating ordered copies ({len(unique_matches)} unique videos)...")
    print("-" * 70)
    
    for i, match in enumerate(unique_matches, 1):
        video_file = match["video_file"]
        new_name = f"{i:02d}_{video_file.stem}{video_file.suffix}"
        new_path = output_folder_path / new_name
        
        shutil.copy2(video_file, new_path)
        
        confidence_icon = "✅" if match["score"] >= min_confidence else "⚠️"
        print(f"{confidence_icon} {i:02d}. {video_file.name} → {new_name}")
        print(f"      Line {match['line_number']}: \"{match['script_line'][:50]}...\"")
        print(f"      Confidence: {match['score']:.2%}")
    
    # Step 5: Save detailed matching report
    report_path = output_folder_path / "_matching_report.txt"
    with open(report_path, "w") as f:
        f.write("VIDEO MATCHING REPORT - LINE BY LINE\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Total script lines: {len(script_lines)}\n")
        f.write(f"Total videos processed: {len(video_transcriptions)}\n")
        f.write(f"Unique videos matched: {len(unique_matches)}\n")
        f.write(f"Total line matches: {len(line_matches)}\n\n")
        f.write("=" * 70 + "\n\n")
        
        for i, match in enumerate(unique_matches, 1):
            f.write(f"VIDEO {i:02d}: {match['video_file'].name}\n")
            f.write(f"  Script Line {match['line_number']}: {match['script_line']}\n")
            f.write(f"  Confidence: {match['score']:.2%}\n")
            f.write(f"  Matched Text: {match['matched_text']}\n")
            f.write(f"  Full Transcription: {video_transcriptions[match['video_file']][:200]}...\n")
            f.write("\n" + "-" * 70 + "\n\n")
        
        # Also list all line matches (including duplicates)
        f.write("\n" + "=" * 70 + "\n")
        f.write("ALL LINE MATCHES (including duplicates):\n")
        f.write("=" * 70 + "\n\n")
        for match in line_matches:
            f.write(f"Line {match['line_number']}: {match['script_line']}\n")
            f.write(f"  → {match['video_file'].name} ({match['score']:.2%})\n\n")
    
    print(f"\n✅ Complete! Ordered videos saved to: {output_folder_path}")
    print(f"📄 Detailed matching report saved to: {report_path}")


print("🚀 Script loaded successfully!")

if __name__ == "__main__":
    print("🎬 Starting video matching process...")
    
    # USAGE:
    # 1. Put all your video clips in a folder (e.g., "totranscribe")
    # 2. Create a text file with your master script (e.g., "master_script.txt")
    # 3. Run this script
    
    try:
        transcribe_and_match_videos(
            video_folder="/Users/nicp/Documents/min vibes/totranscribe",  # Your videos
            master_script_file="/Users/nicp/Documents/min vibes/master_script.txt",  # Your script
            output_folder="ordered_videos",  # Where ordered videos go
            transcription_folder="transcriptions",  # Where transcriptions are saved
            model="base",  # Use "base" for speed, "large-v3" for accuracy
            batch_size=12,
            min_confidence=0.3,  # 30% match threshold
        )
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()