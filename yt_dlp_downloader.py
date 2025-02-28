import customtkinter as tk
import yt_dlp as ydl
import os
import tempfile
from multiprocessing import Manager
import threading
import re
import subprocess
from CTkMessagebox import CTkMessagebox as messagebox
import concurrent.futures

#  EWHQEINQBEJIWQE

# Set the path to whatever you want, the default is the Downloads folder
download_path = os.path.join(os.path.expanduser("~"), "Downloads")

# Set the window size of the application
GUI_WIDTH, GUI_HEIGHT = 700, 200

# Weight for the total progress calculation (arbitrary)
DOWNLOAD_WEIGHT = 0.3
MERGE_WEIGHT = 0.7

# Standard resolutions for the video streams (can be customized)
standard_resolutions = [144, 240, 360, 480, 720, 1080, 1440, 2160, 4320]

# Create the download path if it doesn't exist
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
    
class Download:
    def extract_data(self, url):
        ydl_opts = {"quiet": True,
                    "logger": SilentLogger()}
        try:
            with ydl.YoutubeDL(ydl_opts) as dl:
                video_info = dl.extract_info(url, download=False)
                video_title = video_info["title"]  # Extract video title
                formats = video_info.get("formats", [])
                
                title = "".join(c if c.isalnum() or c in " _-()" else "_" for c in video_title)
                output = f"{download_path}/{title}"
                
                best_audio_stream = None
                stream_map = {}
                resolutions = []
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
                
                return resolutions, stream_map, output
        except Exception as e:
            return e
    
    def progress_hook_v(self, d, queue, download_progress):
        #print("HAHEWQHYEB")
        if d["status"] == "downloading":
            raw_progress = d["_percent_str"]
            progress_clean = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', raw_progress) # Get rid of ANSI escape sequences (color codes)
            try:
                progress = float(progress_clean.strip().replace('%', ''))
                if "temp_video" in d["filename"]:
                    download_progress["video"] = progress
                elif "temp_audio" in d["filename"]:
                    download_progress["audio"] = progress
                
                total_progress = (
                    DOWNLOAD_WEIGHT * ((download_progress["video"] + download_progress["audio"]) / 2)
                )
                
                #print(total_progress)
                queue.put(total_progress / 100)

            except ValueError:
                return

    def download_video(self, stream_map, stream, link, output_path, queue):
        download_progress = {"video": 0, "audio": 0}
        try:
            # Download only audio if the stream is an audio stream
            if stream == "Audio":
                print("test")
                audio_opts = {
                    "format": stream_map.get("Audio"),
                    "outtmpl": f"{output_path}.mp3",  # Save as mp3
                    "quiet": True,
                    "logger": SilentLogger(),
                    "progress_hooks": [lambda d: self.progress_hook_a_stream],
                    'noprogress': True
                }
                with ydl.YoutubeDL(audio_opts) as audio_ydl:
                    audio_ydl.download([link])
                
                #root.download_complete()
            
            # Download video and audio streams separately if the stream is a video stream
            else:
                print("test")
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Temporary video and audio file paths
                    video_temp_path = os.path.join(temp_dir, "temp_video.mp4")
                    audio_temp_path = os.path.join(temp_dir, "temp_audio.m4a")
                    print("test2")
                    print(stream_map)
                    # Download video and audio streams simultaneously
                    video_opts = {
                        "format": stream_map[stream],
                        "outtmpl": video_temp_path,  # Temporary file for video
                        "quiet": True,
                        "logger": SilentLogger(),
                        "progress_hooks": [lambda d: self.progress_hook_v(d, queue, download_progress)],
                        'noprogress': True
                    }
                    print("test3")
                    with ydl.YoutubeDL(video_opts) as video_ydl:
                        print("test4")
                        video_ydl.download([link])
                        #video_thread = threading.Thread(target=video_ydl.download, args=([link]))
                        #video_thread.start()

                    audio_opts = {
                        "format": stream_map.get("Audio"),
                        "outtmpl": audio_temp_path,  # Temporary file for audio
                        "quiet": True,
                        "logger": SilentLogger(),
                        "progress_hooks": [lambda d: self.progress_hook_v(d, queue, download_progress)],
                        'noprogress': True
                    }
                    with ydl.YoutubeDL(audio_opts) as audio_ydl:
                        print("test5")
                        audio_ydl.download([link])
                        #audio_thread = threading.Thread(target=audio_ydl.download, args=([link]))
                        #audio_thread.start()
                    
                    print("test6")
                    
                    # Merge video and audio
                    print("temp location", audio_temp_path, video_temp_path)
                    #self.merge_audio_video(audio_temp_path, video_temp_path)
        except Exception as e:
            print(e)
    
    def merge_audio_video(self, audio_path, video_path):
        command = [
            "ffmpeg",
            "-i", video_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            f"{self.output}.mp4",
            "-y",
        ]

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        
        duration = None
        for line in process.stderr:
            if self.download_cancel_event.is_set():
                process.terminate()  # Kill the ffmpeg process
                process.wait() # Wait for the process to terminate
                #self.gui.download_button.configure(text="Download", state="normal", command=self.gui.start_extract)
                #self.gui.status_label.configure(text="Download cancelled.")
                if os.path.exists(f"{self.output}.mp4"):
                    os.remove(f"{self.output}.mp4")
                return "Download cancelled." # Exit the function early

            if "Duration:" in line and duration is None:
                # Extract duration from FFmpeg output
                match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    duration = hours * 3600 + minutes * 60 + seconds

            if "time=" in line and duration:
                # Extract elapsed time
                match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                if match:
                    hours, minutes, seconds = map(float, match.groups())
                    elapsed_time = hours * 3600 + minutes * 60 + seconds

                    # Calculate merging progress
                    self.download_progress["merge"] = (elapsed_time / duration) * 100
                    total_progress = (
                        DOWNLOAD_WEIGHT * ((self.download_progress["video"] + self.download_progress["audio"]) / 2)
                        + MERGE_WEIGHT * self.download_progress["merge"]
                    )
                    root.update_progress_v(total_progress / 100)
                    #self.gui.update_progress_v(total_progress / 100)

        process.wait()
        root.download_complete()
    
    def cancel_download(self):
        self.is_downloading = False
        root.status_label.configure(text="Cancelling download...")
        self.gui.download_button.configure(state="disabled")


class Gui:
    def __init__(self, root):
        self.root = root
        self.root.title("Youtube downloader")
        
        # Get the screen width and height
        self.screen_width, self.screen_height = root.winfo_screenwidth(), root.winfo_screenheight()

        # Calculate the left and top positions so that our app window is centered
        POS_LEFT = int(self.screen_width / 2 - GUI_WIDTH / 2)
        POS_TOP = int(self.screen_height / 2 - GUI_HEIGHT / 2)
        
        self.root.geometry(f"{GUI_WIDTH}x{GUI_HEIGHT}+{POS_LEFT}+{POS_TOP}")
        self.root.resizable(False, False)
        
        self.executor = concurrent.futures.ProcessPoolExecutor(max_workers=3)
        
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
        self.download = Download()
        self.link = self.user_input.get()
        future = self.executor.submit(self.download.extract_data, self.link)
        
        dots = 0
        def check_future(dots):
            dots = (dots + 1) % 4
            self.status_label.configure(text=f"Extracting data{"." * dots}")
            if future.done():
                try:
                    resolutions, stream_map, output_path = future.result()
                    self.status_label.configure(text="")
                    self.download_window(resolutions, stream_map, output_path)
                except Exception as e:
                    self.status_label.configure(text=e)
                    self.download_button.configure(state="normal")
            else:
                self.root.after(500, lambda: check_future(dots))
        
        self.root.after(500, lambda: check_future(dots))
    
    def download_window(self, resolutions, stream_map, output_path):
        if resolutions is None:
            self.status_label.configure(text="Invalid URL, please try again.")
            self.download_button.configure(state="normal")
            return
        download_toplevel = tk.CTkToplevel()
        download_toplevel.title("Download")
        manager = Manager()
        test_queue = manager.Queue()
        
        # If the user closes the download window rather than selecting a resolution, re-enable the download button
        download_toplevel.protocol("WM_DELETE_WINDOW", self.download_button.configure(state="normal"))
        
        for i, stream in enumerate(resolutions):
            resolution_label = tk.CTkLabel(master=download_toplevel, text=resolutions[i])
            resolution_label.grid(row=i, column=0, padx=5, pady=20)

            button = tk.CTkButton(master=download_toplevel, text="Download", command=lambda element=stream: (download_toplevel.protocol("WM_DELETE_WINDOW", self.download_button.configure(state="disabled")),
                                                                                                             download_toplevel.destroy(),
                                                                                                             self.status_label.configure(text="Starting download..."),
                                                                                                             create_future(element),
                                                                                                             #self.executor.submit(self.download.download_video, stream_map, element, self.link, output_path)
                                                                                                             )
                                  )
            button.grid(row=i, column=1, padx=5, pady=20)
        
        toplevel_width, toplevel_height = 200, 700

        left = int(self.screen_width / 2 - toplevel_width / 2)
        top = int(self.screen_height / 2 - toplevel_height / 2)

        download_toplevel.geometry(f"{toplevel_width}x{toplevel_height}+{left}+{top}")
        download_toplevel.resizable(False, False)
        download_toplevel.grab_set()
        
        def create_future(stream):
            future = self.executor.submit(self.download.download_video, stream_map, stream, self.link, output_path, test_queue)
            self.root.after(100, self.update_progress(future, test_queue))
        
    def update_progress(self, future, queue):
        if future.done():
            try:
                print("Final queue content:", queue)
                self.status_label.configure(text="Download complete!")
            except Exception as e:
                self.status_label.configure(text=e)
                self.download_button.configure(state="normal")
        else:
            try:
                while not queue.empty():
                    progress = queue.get_nowait()
                    self.progress_bar.set(progress)
                    self.status_label.configure(text=f"{progress*100:.2f}%")
            except Exception as e:
                print("Queue error:", e)
            self.root.after(100, lambda: self.update_progress(future, queue))
        

if __name__ == "__main__":
    root = tk.CTk()
    gui = Gui(root)
    root.mainloop()