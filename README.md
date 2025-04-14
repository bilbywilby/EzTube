# EzTube

This script is a complete YouTube downloader GUI application built using Python, PySimpleGUI, and yt-dlp. Here's a brief overview of its key features and functionality:

### Key Features:
1. **GUI for Video Downloads**:
   - Allows users to input a video or playlist URL.
   - Provides options for selecting video format, resolution, audio extraction, and download directory.

2. **Queue System**:
   - Users can add multiple URLs to a download queue.
   - The queue processes downloads one by one in a multithreaded manner using `ThreadPoolExecutor`.

3. **Advanced Options**:
   - Metadata embedding.
   - Thumbnail extraction and saving.
   - Use of FFmpeg for merging files.

4. **Settings**:
   - Users can configure default download settings, themes, and other parameters via a dedicated settings window.
   - Settings are saved in a `config.json` file and loaded at runtime.

5. **Progress and Status Updates**:
   - Displays download progress using a progress bar.
   - Updates the queue and status in real-time.

6. **Dependency Handling**:
   - Automatically checks and installs/updates required Python packages (`yt-dlp`, `PySimpleGUI`, etc.).

7. **Error Handling**:
   - Logs errors to a file (`downloader.log`) and displays error messages in the GUI.

8. **Disk Space Check**:
   - Ensures sufficient disk space before starting a download.

9. **Cross-Platform**:
   - Designed to work on multiple platforms (Windows, macOS, Linux).

### Usage Instructions:
1. Run the script with Python: `python EzTube.py`.
2. Install dependencies automatically if prompted.
3. Use the GUI to add video URLs, configure download settings, and manage the download queue.

### Considerations:
- **FFmpeg**: If advanced merging is enabled, ensure FFmpeg is installed and available in your system's PATH.
- **Error Handling**: Debugging and error handling are robust but may require refinement for specific edge cases.
- **Multithreading**: Care has been taken to handle concurrency with thread-safe queues and thread pools.
