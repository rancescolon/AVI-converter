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
            text=True,
            universal_newlines=True
        )

        progress_val = 0

        while True:
            output_line = process.stdout.readline()
            if output_line == '' and process.poll() is not None:
                break
            if output_line:
                full_output += output_line
                # Update progress based on time if we can parse it
                if "time=" in output_line:
                    try:
                        time_str = output_line.split("time=")[1].split()[0]
                        h, m, s = time_str.split(':')
                        total_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                        # Assuming max duration of 10 minutes for progress calculation
                        progress_val = min(int((total_seconds / 600) * 100), 95)
                    except:
                        progress_val = min(progress_val + 5, 95)
                else:
                    progress_val = min(progress_val + 1, 95)

                progress.progress(progress_val)

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
    finally:
        # Ensure process is terminated
        if 'process' in locals():
            process.terminate()


# Convert button
if st.button("Convert to MP4"):
    if not uploaded_files:
        st.warning("Please upload one or more `.avi` files.")
    else:
        st.info(f"Starting conversion of {len(uploaded_files)} file(s)...")
        success_files = []
        failed_files = []

        for file in uploaded_files:
            with st.expander(f"Converting: {file.name}", expanded=True):
                progress = st.progress(0)
                status_text = st.empty()

                # Save uploaded file temporarily
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".avi") as temp_input:
                        temp_input.write(file.getbuffer())
                        temp_input_path = Path(temp_input.name)

                    # Define output path
                    output_file_path = output_dir / f"{Path(file.name).stem}.mp4"

                    status_text.info(f"Converting {file.name}...")

                    # Convert
                    if convert_to_mp4(temp_input_path, output_file_path, progress):
                        success_files.append((output_file_path, file.name))
                        status_text.success(f"Successfully converted {file.name}!")
                    else:
                        failed_files.append(file.name)
                        status_text.error(f"Failed to convert {file.name}")

                except Exception as e:
                    failed_files.append(file.name)
                    status_text.error(f"Error processing {file.name}: {str(e)}")
                    st.error(traceback.format_exc())
                finally:
                    # Cleanup temp input
                    if 'temp_input_path' in locals():
                        try:
                            temp_input_path.unlink(missing_ok=True)
                        except:
                            pass

        # Show results
        st.subheader("Conversion Results")

        if success_files:
            st.success(f"✅ Successfully converted {len(success_files)} file(s)!")
            for output_path, original_name in success_files:
                with st.expander(f"Download {original_name}", expanded=False):
                    st.download_button(
                        label=f"⬇️ Download {Path(original_name).stem}.mp4",
                        data=output_path.read_bytes(),
                        file_name=f"{Path(original_name).stem}.mp4",
                        mime="video/mp4"
                    )
                    st.video(str(output_path))

        if failed_files:
            st.error(f"❌ Failed to convert {len(failed_files)} file(s):")
            for fname in failed_files:
                st.markdown(f"- `{fname}`")

        # Cleanup old files in output directory (keep only the newly converted ones)
        current_files = {f[0] for f in success_files}
        for existing_file in output_dir.glob("*.mp4"):
            if existing_file not in current_files:
                try:
                    existing_file.unlink()
                except:
                    pass