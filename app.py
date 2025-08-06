import os
import subprocess
import streamlit as st
from pathlib import Path
import shutil
import tempfile
import traceback

# Streamlit page settings
st.set_page_config(page_title="AVI to MP4 Converter", layout="centered")
st.title("🎬 AVI to MP4 Converter")
st.markdown("Upload multiple `.avi` files (max 500MB each) and convert them to `.mp4` using FFmpeg.")

# File uploader
uploaded_files = st.file_uploader("Upload AVI files", type=["avi"], accept_multiple_files=True)

# Output directory
output_dir = Path("converted_videos")
output_dir.mkdir(exist_ok=True)

def convert_to_mp4(input_path: Path, output_path: Path, progress) -> bool:
    command = [
        "ffmpeg",
        "-y",  # Overwrite output file if exists
        "-i", str(input_path),
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-preset", "fast",
        str(output_path)
    ]

    full_output = ""  # Ensure this is always defined

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        progress_val = 0

        while True:
            output_line = process.stdout.readline()
            if output_line == '' and process.poll() is not None:
                break
            if output_line:
                full_output += output_line

            progress_val = min(progress_val + 5, 95)
            progress.progress(progress_val)
            st.sleep(0.1)

        progress.progress(100)

        if process.returncode != 0:
            raise RuntimeError(f"FFmpeg exited with code {process.returncode}")

        return True

    except Exception as e:
        error_message = f"""
        ### ❌ Error converting file: `{input_path.name}`
        **Exception:** `{str(e)}`
        **Traceback:**
        ```
        {traceback.format_exc()}
        ```
        **FFmpeg Output:**
        ```
        {full_output.strip()}
        ```
        """
        st.markdown(error_message)
        print(error_message)
        return False


# Convert button
if st.button("Convert to MP4"):
    if not uploaded_files:
        st.warning("Please upload one or more `.avi` files.")
    else:
        st.info("Starting conversion...")
        success_files = []
        failed_files = []

        for file in uploaded_files:
            st.markdown(f"### 🔄 Converting `{file.name}`")
            progress = st.progress(0)

            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".avi") as temp_input:
                temp_input.write(file.read())
                temp_input_path = Path(temp_input.name)

            # Define output path
            output_file_path = output_dir / f"{temp_input_path.stem}.mp4"

            # Convert
            if convert_to_mp4(temp_input_path, output_file_path, progress):
                success_files.append(output_file_path)
            else:
                failed_files.append(file.name)

            # Cleanup temp input
            temp_input_path.unlink(missing_ok=True)

        # Show results
        if success_files:
            st.success(f"✅ Converted {len(success_files)} file(s)!")
            for f in success_files:
                st.download_button(f"⬇️ Download {f.name}", f.read_bytes(), file_name=f.name)

        if failed_files:
            st.error(f"❌ Failed to convert the following files:")
            for fname in failed_files:
                st.markdown(f"- `{fname}`")
