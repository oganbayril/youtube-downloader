from tkinter import *
from tkinter.ttk import Progressbar, Button
from tkinter import messagebox
from pytube import YouTube
import os
import threading

# python -m pip install git+https://github.com/pytube/pytube for the latest update, if you install pytube from pip it might be outdated.

# Set the path to whatever you want
download_path = "C:/Users/PC/Desktop/youtube downloads"

if os.path.exists(download_path):
    pass
else:  
    os.mkdir(download_path)

def progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    download_percent = int(bytes_downloaded / total_size * 100)
    progress_bar["value"] = download_percent
    status_label["text"] = f"Downloading: {video_title}"
    download_percent_label["text"] = f"{download_percent}%  Downloaded"
    root.update_idletasks()

def complete(stream, file_path):
    status_label["text"] = "Video downloaded successfully!"
    download_percent_label["text"] = ""
    download_button.config(state=NORMAL)
    

def download():
    global video_title
    try:
        download_button.config(state=DISABLED)
        status_label.config(text="")
        link = user_input.get()
        youtube_link = YouTube(link, on_progress_callback=progress, on_complete_callback=complete)
        
        # Sometimes pytube cannot retrieve the title successfully, if it keeps giving the error pytube is most likely broken for the moment.
        try:
            video_title = youtube_link.title
        except:
            messagebox.showinfo("Title error", "Couldn't retrieve the title, please try again.")
            download_button.config(state=NORMAL)
            return youtube_link
            
        confirm = messagebox.askyesno("Are you sure?", f"Do you want to download: {video_title}")
        if confirm is True:
            youtube_download = youtube_link.streams.get_highest_resolution()
            progress_bar["value"] = 0
            # Threading the download so our gui responds at all times
            thread = threading.Thread(target=youtube_download.download, args=(download_path,))
            thread.start()
        elif confirm is False:
            download_button.config(state=NORMAL)
            progress_bar["value"] = 0
            return
        
    except Exception:
        messagebox.showerror("Error", "An error has occured.")
        download_button.config(state=NORMAL)


root = Tk()
root.title("YouTube downloader")
root.geometry("700x150")

info_label = Label(root, text="YouTube link of the video you want to download:")
user_input = Entry(root, width=50)
download_button = Button(root, text="Download", command=download)
progress_bar = Progressbar(root, length=250 , orient=HORIZONTAL)
status_label = Label(root, text="")
download_percent_label = Label(root, text="")

info_label.pack(pady=2)
user_input.pack(pady=2)
download_button.pack(pady=2)
progress_bar.pack(pady=2)
status_label.pack(pady=2)
download_percent_label.pack()
user_input.focus()
root.bind("<Return>", lambda event: download())

root.mainloop()