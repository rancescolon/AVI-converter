import subprocess
import streamlit as st
from pathlib import Path
import tempfile
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

# Streamlit configuration
st.set_page_config(
    page_title="AVI to MP4 Converter",
    layout="wide",
    menu_items={
        'About': "## Fast video conversion using FFmpeg"
    }
)

# Custom CSS
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }

    .stDownloadButton button {
        width: 100%;
        background-color: #4CAF50 !important;
        color: white !important;
        border-radius: 8px;
    }

    .success-message {
        padding: 20px;
        border-radius: 10px;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 20px 0;
    }

    .error-message {
        padding: 15px;
        border-radius: 8px;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 10px 0;
    }

    .loading-dots {
        display: flex;
        gap: 8px;
        justify-content: center;
        align-items: center;
        margin: 20px 0;
    }

    .dot {
        width: 12px;
        height: 12px;
        background-color: #3498db;
        border-radius: 50%;
        animation: pulse 1.4s ease-in-out infinite both;
    }

    .dot:nth-child(1) { animation-delay: -0.32s; }
    .dot:nth-child(2) { animation-delay: -0.16s; }
    .dot:nth-child(3) { animation-delay: 0s; }

    @keyframes pulse {
        0%, 80%, 100% {
            transform: scale(0);
            opacity: 0.5;
        }
        40% {
            transform: scale(1);
            opacity: 1;
        }
    }

    .hidden {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# Constants
OUTPUT_DIR = Path("converted_videos")
OUTPUT_DIR.mkdir(exist_ok=True)
MAX_THREADS = 3  # Adjust based on available resources

# --- Original Backend Functions (Restored) ---
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
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return (True, "")
    except subprocess.CalledProcessError as e:
        return (False, e.stderr)
    except Exception as e:
        return (False, str(e))

def process_file(file, index: int):
    """Process a single file with timing and progress tracking"""
    start = time.time()
    with tempfile.NamedTemporaryFile(suffix=".avi", delete=False) as temp_file: # Added delete=False for explicit cleanup
        temp_file.write(file.getbuffer())
        temp_file.flush()
        temp_input_path = Path(temp_file.name) # Store path for cleanup

        output_filename = f"{Path(file.name).stem}_{index}.mp4"
        output_path = OUTPUT_DIR / output_filename
        success, error = convert_single_video(temp_input_path, output_path)
        duration = time.time() - start

        # Ensure temporary input file is deleted
        if temp_input_path.exists():
            os.unlink(temp_input_path)

        if success:
            if output_path.exists(): # Check if output file was actually created
                with open(output_path, "rb") as f:
                    file_bytes = f.read()
                os.unlink(output_path) # Delete converted file after reading
                return (True, file.name, file_bytes, output_filename, "", duration)
            else:
                return (False, file.name, None, "", "Output file not found after conversion.", duration)
        return (False, file.name, None, "", error, duration)
# --- End Original Backend Functions ---


# Main application
st.title("AVI to MP4 Converter")
st.markdown("Upload an AVI file and convert it to MP4 format quickly and easily.")

# File uploader
uploaded_files = st.file_uploader(
    "Choose a AVI file to convert",
    type=["avi"],
    accept_multiple_files=True,
    help="Select one AVI file"
)

# Limit files for performance
if uploaded_files and len(uploaded_files) > 10:
    st.warning("⚠️ Too prevent Crashing, load files 1 at a time.")
    uploaded_files = uploaded_files[:10]

# Show file info
if uploaded_files:
    st.info(f"📁 {len(uploaded_files)} file ready for conversion")

    # Convert button
    if st.button("🚀 Convert to MP4", type="primary", use_container_width=True):

        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Loading animation container
        loading_container = st.empty()

        # Show loading animation
        with loading_container.container():
            st.markdown("""
            <div class="loading-dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
            <p style="text-align: center; color: #666;">Converting videos...</p>
            """, unsafe_allow_html=True)

        # Process files
        results = []
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
            # Submit all tasks
            futures = [
                executor.submit(process_file, file, i) # Call the original process_file
                for i, file in enumerate(uploaded_files)
            ]

            # Process completed tasks
            completed = 0
            total = len(uploaded_files)

            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append((False, "Unknown", b"", "", str(e), 0.0))

                completed += 1
                progress = completed / total
                progress_bar.progress(progress)
                status_text.text(f"Processed {completed}/{total} files")

        # Hide loading animation
        loading_container.empty()

        # Show results
        total_time = time.time() - start_time
        successful = [r for r in results if r[0]]
        failed = [r for r in results if not r[0]]

        # Success summary
        if successful:
            st.balloons()


            # Download section
            st.subheader("📥 Download Converted File")

            for success, original_name, file_data, output_name, _, duration in successful:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.download_button(
                        label=f"⬇️ {output_name}",
                        data=file_data,
                        file_name=output_name,
                        mime="video/mp4",
                        key=f"download_{output_name}",
                        use_container_width=True
                    )
                with col2:
                    st.text(f"{duration:.1f}s")

        # Show errors if any
        if failed:
            st.subheader("❌ Failed Conversion")
            for success, original_name, _, _, error_msg, duration in failed:
                st.markdown(f"""
                <div class="error-message">
                    <strong>{original_name}</strong><br>
                    Error: {error_msg}<br>
                    Duration: {duration:.1f}s
                </div>
                """, unsafe_allow_html=True)

        # Clear progress indicators
        progress_bar.empty()
        status_text.empty()

else:
    st.markdown("""
    ### 📋 How to use:
    1. Click "Browse file" or drag and drop AVI file
    2. Click "Convert to MP4" to start the conversion
    3. Download your converted MP4 file
    """)