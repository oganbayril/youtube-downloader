# YouTube Downloader

A user-friendly YouTube downloader with a modern GUI that downloads videos in MP4/MP3 formats with multiple quality options.

## Features

- **Modern GUI**: Built with CustomTkinter for a clean, intuitive interface
- **Multiple Quality Options**: Choose from resolutions including 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p (4K), and 4320p (8K)
- **Audio Downloads**: Download audio-only files in MP3 format
- **Real-time Progress Tracking**: Visual progress bar with detailed status updates
- **Safe Operation**: Confirmation dialogs prevent accidental interruption during downloads
- **Process Transparency**: Clear status messages showing current operation (extracting, downloading video+audio, merging, etc.)

## How It Works

1. **Paste URL**: Simply paste any YouTube video URL into the input field
2. **Extract Info**: Click download to extract video information and available formats
3. **Choose Quality**: A new window opens showing all available resolutions and audio options
4. **Download**: Click the button next to your preferred quality to start downloading
5. **Monitor Progress**: Watch the progress bar and status updates as your file downloads

## System Requirements

- Python 3.7+
- FFmpeg (required for video/audio processing)
- Internet connection

## Installation

### Step 1: Install FFmpeg

**IMPORTANT**: You must manually install FFmpeg on your computer before using this downloader.

#### Windows:
1. Visit the official FFmpeg website: https://ffmpeg.org/download.html
2. Download the appropriate version for Windows
3. Extract the downloaded zip file
4. Move the extracted folder to a desired location (e.g., `C:\ffmpeg`)
5. Add FFmpeg to your system PATH:
   - Right-click on "This PC" (or "Computer"), then click "Properties"
   - Click "Advanced system settings", then "Environment Variables"
   - Under "System variables", find and select the "Path" variable, then click "Edit"
   - Click "New" and add the path to the bin folder (e.g., `C:\ffmpeg\bin`)
   - Click "OK" to save changes
6. Verify installation by opening Command Prompt and typing:
   ```
   ffmpeg -version
   ```

#### macOS:
Using Homebrew (recommended):
```bash
brew install ffmpeg
```

Or download from the official website and follow the macOS-specific instructions.

#### Linux:
Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

CentOS/RHEL/Fedora:
```bash
sudo yum install ffmpeg
# or for newer versions:
sudo dnf install ffmpeg
```

### Step 2: Run the Application

#### Using uv (Recommended)
1. Make sure you have Python installed on your system
2. Download or clone this repository to a folder
3. Install uv if you haven't already:
   - Visit [uv's official website](https://docs.astral.sh/uv/)
   - Follow the installation instructions for your operating system
   - Or use the quick install script:
     ```bash
     # On macOS and Linux:
     curl -LsSf https://astral.sh/uv/install.sh | sh
     
     # On Windows:
     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```
4. Install dependencies:
   ```bash
   uv sync
   ```
5. Run the application:
   ```bash
   python main.py
   ```

#### Alternative Installation
1. Make sure you have Python installed on your system
2. Download or clone this repository to a folder
3. Install dependencies manually:
   ```bash
   pip install customtkinter>=5.2.2 yt-dlp>=2025.6.9 ctkmessagebox>=2.7
   ```
4. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. **Launch** the application
2. **Paste** the YouTube video URL in the input field
3. **Click Download** to extract video information
4. **Select Quality** from the popup window showing available options:
   - Video resolutions: 144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p (4K), 4320p (8K)
   - Audio-only option for MP3 downloads
5. **Monitor Progress** through the progress bar and status messages:
   - "Extracting data..."
   - "Downloading audio and video streams separately..."
   - "Downloading audio..." (If user's downloading an audio-only.)
   - "Merging streams..."
   - "Download complete!"

## Safety Features

- **Download Protection**: Confirmation dialog appears if you try to close the application during an active download
- **Error Handling**: Clear error messages for common issues
- **Process Monitoring**: Real-time status updates keep you informed of the current operation

## Troubleshooting

**FFmpeg not found error:**
- Ensure FFmpeg is properly installed and added to your system PATH
- Restart your terminal/command prompt after installation
- Verify with `ffmpeg -version`

**Download fails:**
- Check your internet connection
- Verify the YouTube URL is correct and the video is publicly available
- Some videos may have restrictions that prevent downloading

**Application won't start:**
- Ensure all Python dependencies are installed
- Check that you're using a compatible Python version (3.7+)

## Notes

- Download speeds depend on your internet connection and video file size
- Higher quality videos (1440p, 2160p, 4320p) will take longer to download and require more storage space
- The application respects YouTube's terms of service - only download content you have permission to download

## Support

If you encounter issues, please check that:
1. FFmpeg is properly installed and accessible
2. Your internet connection is stable
3. The YouTube URL is valid and accessible

## License

This project is licensed under the [MIT License](https://opensource.org/licenses/MIT) - see the [LICENSE](LICENSE) file for details.
You are free to use, modify, and distribute this code for personal and commercial purposes.

---

*This tool is for personal use only. Please respect copyright laws and YouTube's terms of service.*