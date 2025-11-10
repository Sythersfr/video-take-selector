"""
Simple Mac M4 transcription script using transcribe-anything (MLX backend).
Uses Apple's MLX acceleration for best speed and multi-language support.
"""

from transcribe_anything import transcribe
from pathlib import Path

def run_mac_transcription(
    source: str,
    output_dir: str = "output",
    model: str = "large-v3",
    batch_size: int = 16,
    prompt: str | None = None,
):
    """
    Transcribe a local file or YouTube URL using Apple Silicon acceleration.

    Args:
        source: Path or URL to video/audio (e.g., 'lecture.mp4' or YouTube link)
        output_dir: Folder to save results (created automatically)
        model: Whisper model name ('tiny', 'small', 'medium', 'large-v3', etc.)
        batch_size: Controls speed vs. memory (M4 handles 12–24 comfortably)
        prompt: Optional custom prompt for better recognition (e.g., domain terms)

    Returns:
        str: Path to output directory with transcripts (txt, srt, vtt, json)
    """
    print("🎧 Starting transcription with Apple MLX backend...")
    print(f"🔹 Source: {source}")
    print(f"🔹 Model: {model}, Batch size: {batch_size}")
    if prompt:
        print(f"🔹 Custom prompt: {prompt}")

    output_path = transcribe(
        url_or_file=source,
        output_dir=output_dir,
        model=model,
        device="mlx",  # Apple Silicon optimized backend
        other_args=[
            "--batch_size", str(batch_size),
            "--verbose",  # show live progress
        ],
        initial_prompt=prompt,
    )

    print(f"\n✅ Transcription complete!")
    print(f"📁 Output saved in: {output_path}")
    return output_path


def transcribe_folder(
    folder_path: str,
    video_extensions: tuple = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"),
    audio_extensions: tuple = (".mp3", ".wav", ".m4a", ".flac", ".aac"),
    output_base_dir: str = "output",
    model: str = "large-v3",
    batch_size: int = 12,
    prompt: str | None = None,
):
    """
    Transcribe all video/audio files in a folder.
    
    Args:
        folder_path: Path to folder containing media files
        video_extensions: Tuple of video file extensions to process
        audio_extensions: Tuple of audio file extensions to process
        output_base_dir: Base directory for outputs (each file gets its own subfolder)
        model: Whisper model name
        batch_size: Batch size for processing
        prompt: Optional prompt for all files
    """
    folder = Path(folder_path)
    all_extensions = video_extensions + audio_extensions
    
    # Find all media files
    media_files = [f for f in folder.iterdir() if f.suffix.lower() in all_extensions]
    
    if not media_files:
        print(f"❌ No media files found in {folder_path}")
        print(f"   Looking for: {', '.join(all_extensions)}")
        return
    
    print(f"\n📂 Found {len(media_files)} media file(s) to transcribe")
    print("=" * 60)
    
    for i, media_file in enumerate(media_files, 1):
        print(f"\n🎬 Processing {i}/{len(media_files)}: {media_file.name}")
        print("-" * 60)
        
        # Create unique output folder for each file
        output_dir = f"{output_base_dir}/{media_file.stem}"
        
        try:
            run_mac_transcription(
                source=str(media_file),
                output_dir=output_dir,
                model=model,
                batch_size=batch_size,
                prompt=prompt,
            )
        except Exception as e:
            print(f"❌ Error processing {media_file.name}: {e}")
            continue
    
    print(f"\n🎉 Batch transcription complete! Processed {len(media_files)} files.")


if __name__ == "__main__":
    # Option 1: Transcribe a single file
    # run_mac_transcription(
    #     source="C0032.mp4",
    #     model="large-v3",
    #     batch_size=12,
    #     prompt=None,
    # )
    
    # Option 2: Transcribe all videos in current folder
    transcribe_folder(
        folder_path="/Users/nicp/Documents/min vibes/totranscribe",  # Current folder (or specify path like "/Users/nicp/Documents/min vibes")
        model="large-v3",
        batch_size=12,
        prompt=None,  # Set to None or add your custom prompt
    )