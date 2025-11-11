"""
Add Background Music to Video
Downloads audio from URL and adds it as background music to your video.
Automatically adjusts levels so dialogue is clear.
"""

import subprocess
import tempfile
from pathlib import Path
import argparse


def download_audio(url: str, output_path: str) -> bool:
    """Download audio from URL using yt-dlp."""
    print(f"📥 Downloading audio from: {url}")
    
    cmd = [
        'yt-dlp',
        '-x',  # Extract audio
        '--audio-format', 'mp3',
        '--audio-quality', '0',  # Best quality
        '-o', output_path,
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Audio downloaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading audio: {e.stderr}")
        return False


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(video_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, TypeError):
        return 0.0


def add_background_music(
    video_path: str,
    music_url: str,
    output_path: str = "video_with_music.mp4",
    music_volume: float = 0.15,
    dialogue_volume: float = 1.0,
    fade_in: float = 2.0,
    fade_out: float = 3.0,
    loop_music: bool = True
):
    """
    Add background music to video with smart mixing.
    
    Args:
        video_path: Path to input video
        music_url: URL to download music from (YouTube, SoundCloud, etc.)
        output_path: Path for output video
        music_volume: Background music volume (0.0 to 1.0, default 0.15)
        dialogue_volume: Dialogue volume (default 1.0)
        fade_in: Fade in duration in seconds
        fade_out: Fade out duration in seconds
        loop_music: Loop music to match video duration
    """
    
    print("\n🎵 Adding Background Music to Video")
    print("=" * 70)
    print(f"📹 Video: {video_path}")
    print(f"🎼 Music URL: {music_url}")
    print(f"🔊 Music volume: {music_volume * 100:.0f}%")
    print(f"🎤 Dialogue volume: {dialogue_volume * 100:.0f}%")
    print()
    
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return False
    
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    temp_audio = temp_dir / "background_music.mp3"
    
    try:
        # Download music
        if not download_audio(music_url, str(temp_audio)):
            return False
        
        # Get video duration
        video_duration = get_video_duration(video_path)
        print(f"📊 Video duration: {video_duration:.2f} seconds")
        
        # Build ffmpeg command with filter complex
        print("\n🎛️  Mixing audio...")
        
        # Filter for background music
        music_filters = [
            f"volume={music_volume}",  # Reduce music volume
            f"afade=t=in:st=0:d={fade_in}",  # Fade in
            f"afade=t=out:st={video_duration - fade_out}:d={fade_out}",  # Fade out
        ]
        
        if loop_music:
            music_filters.insert(0, f"aloop=loop=-1:size=2e+09")  # Loop infinitely
        
        music_filter = ",".join(music_filters)
        
        # Dialogue filter
        dialogue_filter = f"volume={dialogue_volume}"
        
        # FFmpeg command with advanced audio mixing
        cmd = [
            'ffmpeg',
            '-i', str(video_path),  # Input video
            '-i', str(temp_audio),  # Input music
            '-filter_complex',
            f"[1:a]{music_filter}[music];"  # Process music
            f"[0:a]{dialogue_filter}[dialogue];"  # Process dialogue
            f"[dialogue][music]amix=inputs=2:duration=first:dropout_transition=0[aout]",  # Mix both (dialogue first to prioritize)
            '-map', '0:v',  # Use video from input 0
            '-map', '[aout]',  # Use mixed audio
            '-c:v', 'copy',  # Copy video (no re-encoding)
            '-c:a', 'aac',  # Encode audio as AAC
            '-b:a', '192k',  # Audio bitrate
            '-shortest',  # Stop when shortest input ends
            '-y',
            str(output_path)
        ]
        
        print("🎬 Processing video... (this may take a few minutes)")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            return False
        
        print(f"\n✅ Success! Video with music saved to: {output_path}")
        print(f"📁 File size: {Path(output_path).stat().st_size / 1024 / 1024:.1f} MB")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        # Cleanup temp files
        if temp_audio.exists():
            temp_audio.unlink()
        if temp_dir.exists():
            temp_dir.rmdir()


def add_background_music_simple(
    video_path: str,
    music_file: str,
    output_path: str = "video_with_music.mp4",
    music_volume: float = 0.15
):
    """
    Simple version: Add background music from local file.
    
    Args:
        video_path: Path to input video
        music_file: Path to local music file
        output_path: Path for output video
        music_volume: Background music volume (0.0 to 1.0)
    """
    
    print("\n🎵 Adding Background Music (Local File)")
    print("=" * 70)
    
    video_path = Path(video_path)
    music_path = Path(music_file)
    
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        return False
    
    if not music_path.exists():
        print(f"❌ Music file not found: {music_path}")
        return False
    
    video_duration = get_video_duration(video_path)
    
    cmd = [
        'ffmpeg',
        '-i', str(video_path),
        '-i', str(music_path),
        '-filter_complex',
        f"[1:a]aloop=loop=-1:size=2e+09,volume={music_volume},"
        f"afade=t=in:st=0:d=2,afade=t=out:st={video_duration-3}:d=3[music];"
        f"[0:a]volume=1.0[dialogue];"
        f"[dialogue][music]amix=inputs=2:duration=first:dropout_transition=0[aout]",
        '-map', '0:v',
        '-map', '[aout]',
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-shortest',
        '-y',
        str(output_path)
    ]
    
    print("🎬 Processing...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ Success! Video saved to: {output_path}")
        return True
    else:
        print(f"❌ Error: {result.stderr}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Add background music to video from URL or local file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # From YouTube URL
  python add_background_music.py video.mp4 "https://youtube.com/watch?v=..."
  
  # From local file
  python add_background_music.py video.mp4 music.mp3 --local
  
  # Custom volumes
  python add_background_music.py video.mp4 "URL" --music-volume 0.2 --dialogue-volume 1.2
  
  # Custom output name
  python add_background_music.py video.mp4 "URL" -o final_video.mp4
        """
    )
    
    parser.add_argument('video', help='Input video file')
    parser.add_argument('music', help='Music URL or local file path')
    parser.add_argument('-o', '--output', default='video_with_music.mp4',
                        help='Output video path (default: video_with_music.mp4)')
    parser.add_argument('--local', action='store_true',
                        help='Use local music file instead of URL')
    parser.add_argument('--music-volume', type=float, default=0.15,
                        help='Background music volume 0.0-1.0 (default: 0.15)')
    parser.add_argument('--dialogue-volume', type=float, default=1.0,
                        help='Dialogue volume 0.0-2.0 (default: 1.0)')
    parser.add_argument('--fade-in', type=float, default=2.0,
                        help='Fade in duration in seconds (default: 2.0)')
    parser.add_argument('--fade-out', type=float, default=3.0,
                        help='Fade out duration in seconds (default: 3.0)')
    parser.add_argument('--no-loop', action='store_true',
                        help='Don\'t loop music to match video duration')
    
    args = parser.parse_args()
    
    if args.local:
        # Use local file
        success = add_background_music_simple(
            args.video,
            args.music,
            args.output,
            args.music_volume
        )
    else:
        # Download from URL
        success = add_background_music(
            args.video,
            args.music,
            args.output,
            args.music_volume,
            args.dialogue_volume,
            args.fade_in,
            args.fade_out,
            not args.no_loop
        )
    
    exit(0 if success else 1)

