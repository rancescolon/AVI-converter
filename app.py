import subprocess
import streamlit as st
from pathlib import Path
import tempfile
import os

# Streamlit configuration
st.set_page_config(page_title="AVI to MP4 Converter", layout="centered")
st.title("🎬 AVI to MP4 Converter")
st.caption("Upload multiple AVI files (max 500MB each) for conversion to MP4")

# Constants
OUTPUT_DIR = Path("converted_videos")
OUTPUT_DIR.mkdir(exist_ok=True)

def convert_video(input_path: Path, output_path: Path, progress_bar) -> bool:
    """Convert video file using FFmpeg with progress tracking"""
    try:
        cmd = [
            "ffmpeg",
            "-y",  # Overwrite without asking
            "-i", str(input_path),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-b:a", "192k",
            "-preset", "fast",
            "-v", "error",
            str(output_path)
        ]

        process = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Simulate progress since we can't get real progress from ffmpeg
        for percent in range(0, 101, 20):
            progress_bar.progress(percent)

        return True

    except subprocess.CalledProcessError as e:
        st.error(f"FFmpeg error: {e.stderr}")
        return False
    except Exception as e:
        st.error(f"Conversion error: {str(e)}")
        return False

# Main application
uploaded_files = st.file_uploader(
    "Select AVI files",
    type=["avi"],
    accept_multiple_files=True
)

if uploaded_files:
    if st.button("Start Conversion", type="primary"):
        success_count = 0

        for file in uploaded_files:
            with st.expander(f"Processing: {file.name}", expanded=True):
                progress = st.progress(0)
                status = st.empty()

                # Create temp file
                with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as temp_file:
                    temp_path = temp_file.name
                    temp_file.write(file.read())

                try:
                    output_path = OUTPUT_DIR / f"{Path(file.name).stem}.mp4"
                    status.info(f"Converting {file.name}...")

                    if convert_video(Path(temp_path), output_path, progress):
                        success_count += 1
                        progress.progress(100)
                        status.success("Conversion successful!")

                        # Show download button
                        with open(output_path, "rb") as f:
                            st.download_button(
                                "Download MP4",
                                f.read(),
                                file_name=output_path.name,
                                mime="video/mp4"
                            )
                    else:
                        status.error("Conversion failed")

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)

        # Summary
        if success_count > 0:
            st.balloons()
            st.success(f"Successfully converted {success_count}/{len(uploaded_files)} files")
        else:
            st.error("No files were successfully converted")
else:
    st.warning("Please upload at least one AVI file first")