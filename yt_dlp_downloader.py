import customtkinter as tk
import yt_dlp as ydl
import os
import tempfile
from multiprocessing import Manager
import re
import subprocess
from CTkMessagebox import CTkMessagebox as messagebox
import concurrent.futures

# Set the path to whatever you want, the default is the Downloads folder
download_path = os.path.join(os.path.expanduser("~"), "Downloads")

# Set the window size of the application
GUI_WIDTH, GUI_HEIGHT = 700, 200

# Weight for the total progress calculation (arbitrary)
DOWNLOAD_WEIGHT = 0.3
MERGE_WEIGHT = 0.7

# Standard resolutions for the video streams (can be customized)
standard_resolutions = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

if os.path.exists(download_path):
    pass
else:  
    os.mkdir(download_path)

# Logger class to suppress terminal messages from yt-dlp
class SilentLogger:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass

# Custom exception for when the download is cancelled
class DownloadCancelled(Exception):
    pass
    
class Downloader:
    def get_unique_filename(self, filepath, format):
        file = f"{filepath}.{format}"
        counter = 1
        while os.path.exists(file):
            file = f"{filepath} ({counter}).{format}"
            counter += 1
        return file
    
    def extraction_progress_hook(self, d, cancel_event):
        if cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user.")
    
    def extract_data(self, url, cancel_event):
        possible_errors = {
            ydl.utils.DownloadError: "Download error, please check the URL or your internet connection.",
            ydl.utils.ExtractorError: "Extractor error, this might be due to an unsupported site or a problem with the video.",
            ydl.utils.RegexNotFoundError: "Regex error, the video URL might be incorrect or the site structure has changed.",
            ydl.utils.GeoRestrictedError: "Geo-restricted video, this video is not available in your region.",
                           }
        
        ydl_opts = {"quiet": True,
                    "logger": SilentLogger(),
                    "progress_hooks": [lambda d: self.extraction_progress_hook(d, cancel_event)],}
        try:
            with ydl.YoutubeDL(ydl_opts) as dl:
                video_info = dl.extract_info(url, download=False)
                video_title = video_info["title"]
                formats = video_info.get("formats", [])
                duration = video_info.get("duration") 
                title = "".join(c if c.isalnum() or c in " _-()" else "_" for c in video_title)
                output = f"{download_path}/{title}"          
                best_audio_stream = None
                stream_map = {}
                resolutions = []
                
                if 'is_live' in video_info and video_info['is_live']: # TODO: ADD LIVESTREAM SUPPORT IN THE FUTURE
                    return "Live streams are not supported.", None, None, None
                
                for stream in formats:
                    if stream.get("vcodec") != "none" and stream.get("acodec") == "none":  # Video-only streams
                        height = stream.get("height")
                        if height is not None and height in standard_resolutions:
                            resolution = f"{height}p"
                            resolutions.append(resolution)
                            stream_map[resolution] = stream["format_id"]
                    elif stream.get("acodec") != "none" and stream.get("vcodec") == "none":  # Audio-only streams
                        abr = stream.get("abr")
                        # If average bitrate is None, handle it by falling back to the first available stream
                        if abr is None:
                            if best_audio_stream is None:  # If no stream has been chosen yet, pick this one
                                best_audio_stream = stream
                        else:
                            if best_audio_stream.get("abr") is None or abr > best_audio_stream.get("abr"):
                                best_audio_stream = stream
                
                # Sort video streams by resolution (descending)
                resolutions = sorted(set(resolutions), key=lambda x: int(x[:-1]), reverse=True)
                
                resolutions.append("Audio")
                stream_map["Audio"] = best_audio_stream["format_id"]
                
                return resolutions, stream_map, output, duration
        except tuple(possible_errors.keys()) as e:
            return possible_errors[type(e)], None, None, None
        
        except Exception:
            return (None,) * 4
    
    def progress_hook(self, d, queue, download_progress, cancel_event):
        if cancel_event.is_set():
            raise DownloadCancelled("Download cancelled by user.")
        
        if d["status"] == "downloading":
            try:
                raw_progress = d["_percent_str"]
                progress_clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', raw_progress) # Get rid of ANSI escape sequences (color codes)
                progress = float(progress_clean.strip().replace('%', ''))
                # Seperate video and audio progress if the stream is a video stream
                if "video" in download_progress:
                    if "temp_video" in d["filename"]:
                        download_progress["video"] = progress
                    elif "temp_audio" in d["filename"]:
                        download_progress["audio"] = progress
                    
                    total_progress = (
                        DOWNLOAD_WEIGHT * ((download_progress["video"] + download_progress["audio"]) / 2)
                        + MERGE_WEIGHT * download_progress["merge"]
                    )
                    queue.put(total_progress / 100)
                # If the stream is an audio stream, just put the progress in the queue
                else:
                    queue.put(progress / 100)    
            except Exception as e:
                queue.put(e)

    def download_video(self, stream_map, stream, link, output, queue, cancel_event, duration):
        try:
            # Download only audio if the stream is an audio stream
            if stream == "Audio":
                download_progress = {"audio": 0}
                output = self.get_unique_filename(output, "mp3")
                audio_opts = {
                    "format": stream_map.get("Audio"),
                    "outtmpl": output,
                    "quiet": True,
                    "logger": SilentLogger(),
                    "progress_hooks": [lambda d: self.progress_hook(d, queue, download_progress, cancel_event)],
                    'noprogress': True
                }
                with ydl.YoutubeDL(audio_opts) as audio_ydl:
                    audio_ydl.download([link])
                return "Download completed."
            
            # Download video and audio streams separately if the stream is a video stream
            else:
                download_progress = {"video": 0, "audio": 0, "merge": 0}
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Temporary video and audio file paths so the download path is clean
                    video_temp_path = os.path.join(temp_dir, "temp_video.mp4")
                    audio_temp_path = os.path.join(temp_dir, "temp_audio.m4a")

                    # Download video and audio streams simultaneously
                    audio_opts = {
                        "format": stream_map.get("Audio"),
                        "outtmpl": audio_temp_path,  # Temporary file for audio
                        "quiet": True,
                        "logger": SilentLogger(),
                        "progress_hooks": [lambda d: self.progress_hook(d, queue, download_progress, cancel_event)],
                        "noprogress": True,
                    }
                    
                    video_opts = {
                        "format": stream_map[stream],
                        "outtmpl": video_temp_path,  # Temporary file for video
                        "quiet": True,
                        "logger": SilentLogger(),
                        "progress_hooks": [lambda d: self.progress_hook(d, queue, download_progress, cancel_event)],
                        "noprogress": True,
                    }
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        video_future = executor.submit(ydl.YoutubeDL(video_opts).download, [link])
                        audio_future = executor.submit(ydl.YoutubeDL(audio_opts).download, [link])
                        concurrent.futures.wait([video_future, audio_future])
                    
                    # Merge video and audio streams       
                    self.merge_audio_video(audio_temp_path, video_temp_path, output, download_progress, queue, cancel_event, duration)
                    return "Download completed."
        except Exception as e:
            return e
    
    def merge_audio_video(self, audio_path, video_path, output, download_progress , queue, cancel_event, duration):
        output = self.get_unique_filename(output, "mp4")
        command = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-y",
            output,
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",      # Specify an encoding, utf-8 seems good enough
            errors="replace"       # Replace any problematic characters
        )

        for line in process.stderr:
            if cancel_event.is_set():
                process.terminate()
                process.wait()
                if os.path.exists(output):
                    os.remove(output)
                raise DownloadCancelled("Download cancelled by user.")
            
            if "time=" in line and duration:
                # Extract elapsed time
                match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    elapsed_time = hours * 3600 + minutes * 60 + seconds

                    # Calculate merging progress
                    download_progress["merge"] = (elapsed_time / duration) * 100
                    total_progress = (
                        DOWNLOAD_WEIGHT * ((download_progress["video"] + download_progress["audio"]) / 2)
                        + MERGE_WEIGHT * download_progress["merge"]
                    )
                    queue.put(total_progress / 100)
        process.wait()
        
        
        
        
class Gui:
    def __init__(self, root):
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)
        self.is_extracting = False
        self.is_downloading = False
        self.message = None
        self.manager = Manager()
        self.progress_queue = self.manager.Queue()
        self.cancel_event = self.manager.Event()
        
        self.root = root
        self.root.title("Youtube downloader")
        root.protocol("WM_DELETE_WINDOW", self.close_gui)
        
        # Get the screen width and height
        self.screen_width, self.screen_height = root.winfo_screenwidth(), root.winfo_screenheight()

        # Calculate the left and top positions so that our app window is centered
        POS_LEFT = int(self.screen_width / 2 - GUI_WIDTH / 2)
        POS_TOP = int(self.screen_height / 2 - GUI_HEIGHT / 2)
        
        self.root.geometry(f"{GUI_WIDTH}x{GUI_HEIGHT}+{POS_LEFT}+{POS_TOP}")
        self.root.resizable(False, False)
        
        self.info_label = tk.CTkLabel(master=root, text="YouTube link of the video you want to download:")
        self.user_input = tk.CTkEntry(master=root, placeholder_text="Insert link here", width=300)
        self.link = None
        self.status_label = tk.CTkLabel(master=root, text="")
        self.download_button = tk.CTkButton(master=root, text="Download", command=self.start_extract)
        self.progress_bar = tk.CTkProgressBar(master=root, width=250, height=20)
        self.progress_bar.set(0)

        self.info_label.pack(pady=2)
        self.user_input.pack(pady=2)
        self.download_button.pack(pady=10)
        self.progress_bar.pack(pady=5)
        self.status_label.pack(pady=2)
    
    def start_extract(self):
        if not self.user_input.get():
            self.status_label.configure(text="Please insert a link")
            return
        self.progress_bar.set(0)
        self.download_button.configure(state="disabled")
        self.downloader = Downloader()
        self.link = self.user_input.get()
        future = self.executor.submit(self.downloader.extract_data, self.link, self.cancel_event)
        self.is_extracting = True
        
        dots = 0
        def check_future(dots):
            dots = (dots + 1) % 4
            self.status_label.configure(text=f"Extracting data{"." * dots}")
            if future.done():
                try:
                    resolutions, stream_map, output_path, duration = future.result()
                    self.status_label.configure(text="")
                    self.is_extracting = False
                    if self.cancel_event.is_set():
                        self.cancel_event.clear()
                    if self.message:
                        self.close_messagebox()
                    self.download_window(resolutions, stream_map, output_path, duration)
                except Exception as e:
                    self.status_label.configure(text=e)
                    self.download_button.configure(state="normal")
            else:
                self.root.after(500, lambda: check_future(dots))
        
        self.root.after(500, lambda: check_future(dots))
    
    def download_window(self, resolutions, stream_map, output_path, duration):
        if resolutions is None:
            self.status_label.configure(text="An unexpected error occured, please try again.")
            self.download_button.configure(state="normal")
            return
        if resolutions == "Live streams are not supported.":
            self.status_label.configure(text="Live streams are not supported.")
            self.download_button.configure(state="normal")
            return
        if all(_ is None for _ in (stream_map, output_path, duration)):
            self.status_label.configure(text=resolutions)
            self.download_button.configure(state="normal")
            return
        download_toplevel = tk.CTkToplevel()
        download_toplevel.title("Download")
        video_title = os.path.basename(output_path)
        
        # Calculate the left and top positions so that our download window is centered
        toplevel_width, toplevel_height = 200, 700
        left = int(self.screen_width / 2 - toplevel_width / 2)
        top = int(self.screen_height / 2 - toplevel_height / 2)
        download_toplevel.geometry(f"{toplevel_width}x{toplevel_height}+{left}+{top}")
        download_toplevel.resizable(False, False)
        download_toplevel.grab_set()
        
        # If the user closes the download window rather than selecting a resolution, re-enable the download button
        download_toplevel.protocol("WM_DELETE_WINDOW", self.download_button.configure(state="normal"))
        
        for i, stream in enumerate(resolutions):
            resolution_label = tk.CTkLabel(master=download_toplevel, text=resolutions[i])
            resolution_label.grid(row=i, column=0, padx=5, pady=20)

            button = tk.CTkButton(master=download_toplevel, text="Download", command=lambda element=stream: (
                                                                                                             download_toplevel.destroy(),
                                                                                                             self.status_label.configure(text=f"Starting to download {video_title}..."), 
                                                                                                             create_future(element),
                                                                                                             self.download_button.configure(text="Cancel download", command=lambda: self.cancel_download(self.cancel_event))
                                                                                                             )
                                  )
            button.grid(row=i, column=1, padx=5, pady=20)
        
        def create_future(stream):
            self.is_downloading = True
            future = self.executor.submit(self.downloader.download_video, stream_map, stream, self.link, output_path, self.progress_queue, self.cancel_event, duration)
            self.root.after(100, self.update_progress(future, self.progress_queue, stream, output_path))
    
    def cancel_download(self, cancel_event):
        cancel_event.set()
        self.status_label.configure(text="Cancelling download...")
        
    def update_progress(self, future, queue, stream, output_path):
        if future.done():
            try:
                self.is_downloading = False
                result = future.result()
                if self.message:
                    self.close_messagebox()
                if type(result) is DownloadCancelled:
                    self.cancel_event.clear()
                    self.status_label.configure(text="Download cancelled by user.")
                    output = self.downloader.get_unique_filename(output_path, "mp3")
                    if os.path.exists(f"{output}.part"): # Delete the .part file if the user cancels the mp3 download
                        os.remove(f"{output}.part")
                elif result == "Download completed.":
                    self.status_label.configure(text="Download completed.")
                    self.progress_bar.set(1)
                else:
                    self.status_label.configure(text=f"Error: {result}")
                self.download_button.configure(text="Download", state="normal", command=self.start_extract)
                while not self.progress_queue.empty():
                    self.progress_queue.get()
                
            except Exception as e:
                self.status_label.configure(text=f"Error: {e}")
                self.download_button.configure(state="normal")
        else:
            try:
                while not queue.empty():
                    progress = queue.get_nowait()
                    if stream == "Audio":
                        self.status_label.configure(text=f"Downloading audio...    {progress*100:.2f}%")
                    else:
                        if progress < DOWNLOAD_WEIGHT:
                            self.status_label.configure(text=f"Downloading audio and video streams seperately...    {progress*100:.2f}%")
                        elif progress == DOWNLOAD_WEIGHT:
                            self.status_label.configure(text=f"Seperate streams downloaded, waiting to merge...    {progress*100:.2f}%")
                        else:
                            self.status_label.configure(text=f"Merging streams...    {progress*100:.2f}%")
                    self.progress_bar.set(progress)
            except Exception as e:
                print("Queue error:", e)
            self.root.after(100, lambda: self.update_progress(future, queue, stream, output_path))
    
    def close_gui(self):
        status = {
            "extraction": self.is_extracting,
            "download": self.is_downloading
        }

        event_status = [key for key, value in status.items() if value]
        
        if event_status:
            self.message_closed = False
            self.message = messagebox(title="Are you sure?",
                    message=f"Do you want to stop the {event_status[0]} and close the application?",
                    icon="question",
                    option_1="No",
                    option_2="Yes",
                    sound=True,
                    option_focus=1
                    )
            if not self.message_closed:  # Only get response if messagebox is still active
                self.response = self.message.get()
                if self.response == "Yes":
                    self.cancel_download(self.cancel_event)
                    self.root.destroy()
        else:
            self.root.destroy()
    
    def close_messagebox(self):
        if self.message.winfo_exists():
            self.message.event_generate("<Escape>")
            self.message_closed = True  # Set the flag to True to indicate that the messagebox has been closed
            self.message = None
    
if __name__ == "__main__":
    root = tk.CTk()
    gui = Gui(root)
    root.mainloop()