import subprocess
import streamlit as st
from pathlib import Path
import tempfile
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

# Streamlit configuration
st.set_page_config(
    page_title="⚡ Lightning Fast AVI to MP4 Converter",
    layout="wide",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'About': "## Ultra-fast video conversion using FFmpeg"
    }
)
st.title("⚡ Lightning Fast AVI to MP4 Converter")
st.caption("Upload multiple AVI files for efficient conversion to MP4")

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #4CAF50; }
    .st-b7 { color: white; }
    .stDownloadButton button {
        width: 100%;
        background-color: #4CAF50 !important;
        color: white !important;
    }
    .file-card {
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        background-color: #f0f2f6;
    }
    .success-card { border-left: 5px solid #4CAF50; }
    .error-card { border-left: 5px solid #f44336; }
</style>
""", unsafe_allow_html=True)

# Constants
OUTPUT_DIR = Path("converted_videos")
OUTPUT_DIR.mkdir(exist_ok=True)
MAX_THREADS = 3  # Optimal for Streamlit Cloud resources

def convert_single_video(input_path: Path, output_path: Path) -> Tuple[bool, str]:
    """Convert a single video file using optimized FFmpeg commands"""
    try:
        cmd = [
            "ffmpeg",
            "-y", "-i", str(input_path),
            "-c:v", "libx264", "-preset", "superfast",
            "-crf", "23",  # Balanced quality/size
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            "-threads", "2",  # Limit threads per conversion
            "-v", "error",
            str(output_path)
        ]

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True
        )
        return (True, "")
    except subprocess.CalledProcessError as e:
        return (False, e.stderr)
    except Exception as e:
        return (False, str(e))

def process_file(file, index: int):
    """Process a single file with progress tracking"""
    with tempfile.NamedTemporaryFile(suffix=".avi") as temp_file:
        temp_file.write(file.getbuffer())
        temp_file.flush()

        output_filename = f"{Path(file.name).stem}_{index}.mp4"
        output_path = OUTPUT_DIR / output_filename

        success, error = convert_single_video(Path(temp_file.name), output_path)

        if success:
            with open(output_path, "rb") as f:
                file_bytes = f.read()
            os.unlink(output_path)
            return (True, file.name, file_bytes, output_filename, "")
        return (False, file.name, None, "", error)

# Main application
uploaded_files = st.file_uploader(
    "Drag and drop AVI files here",
    type=["avi"],
    accept_multiple_files=True,
    help="Maximum 10 files at once for optimal performance"
)

if uploaded_files and len(uploaded_files) > 10:
    st.warning("For best performance, please upload no more than 10 files at once")
    uploaded_files = uploaded_files[:10]

if uploaded_files:
    if st.button("🚀 Start Conversion", type="primary", use_container_width=True):
        start_time = time.time()
        progress_bar = st.progress(0)
        status_area = st.empty()

        with status_area.container():
            st.subheader("Conversion Progress")
            progress_text = st.empty()
            results = []

            # Process files with ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
                futures = []

                # Submit all files for processing
                for i, file in enumerate(uploaded_files):
                    futures.append(executor.submit(process_file, file, i))

                # Monitor progress
                completed = 0
                total = len(uploaded_files)

                for future in futures:
                    try:
                        result = future.result()
                        results.append(result)
                        completed += 1
                        progress = int((completed / total) * 100)
                        progress_bar.progress(progress)
                        progress_text.text(f"Processed {completed}/{total} files")
                    except Exception as e:
                        st.error(f"Error processing file: {str(e)}")

            # Display results
            success_count = sum(1 for r in results if r[0])
            conversion_time = time.time() - start_time

            if success_count > 0:
                st.balloons()
                st.success(f"""
                ### 🎉 Successfully converted {success_count}/{len(uploaded_files)} files
                ⏱️ Total conversion time: {conversion_time:.2f} seconds
                """)

                with st.expander("📥 Download Converted Files", expanded=True):
                    for success, name, data, output_name, error in results:
                        if success:
                            with st.container():
                                st.download_button(
                                    label=f"Download {output_name}",
                                    data=data,
                                    file_name=output_name,
                                    mime="video/mp4",
                                    key=f"dl_{output_name}"
                                )
                        else:
                            st.error(f"Failed to convert {name}: {error}")
            else:
                st.error("❌ No files were successfully converted")
else:
    st.info("ℹ️ Please upload AVI files to begin conversion")