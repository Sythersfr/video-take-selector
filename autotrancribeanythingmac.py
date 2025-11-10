"""
Simple Mac M4 transcription script using transcribe-anything (MLX backend).
Uses Apple's MLX acceleration for best speed and multi-language support.
"""

from transcribe_anything import transcribe

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


if __name__ == "__main__":
    # Example usage — you can replace with your local file path or URL
    # For YouTube: source="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    # For local file: source="path/to/your/audio.mp3" or "video.mp4"
    run_mac_transcription(
        source="C0032.mp4",  # Replace with your local file path
        model="large-v3",
        batch_size=12,  # Reduced for better stability
        prompt="The speaker is an actor and hes acting out a scene",
    )
