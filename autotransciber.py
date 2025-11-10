# from transcribe_anything import transcribe

# # Direct prompt
# transcribe(
#     url_or_file="video.mp4",
#     initial_prompt="The speaker discusses AI, PyTorch, TensorFlow, and deep learning algorithms."
# )

# # Load prompt from file
# with open("my_prompt.txt", "r") as f:
#     prompt = f.read()

# transcribe(
#     url_or_file="https://www.youtube.com/shorts/oy9Xo4BY3Bs",
#     initial_prompt=prompt
# )


# transcribe_minimal.py
from transcribe_anything import transcribe

out_dir = transcribe(
    url_or_file="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    output_dir="out",                 # folder is created if it doesn't exist
)
print("Outputs written to:", out_dir)
