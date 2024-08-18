import requests
import tkinter as tk
from tkinter import ttk
from threading import Thread
from threading import Lock
import time
url_list = []
thread_list = []


def cold_update_github_links():
    url_list.clear()
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/IME%20Interpreter%20V5.0.exe')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/IME%20Interpreter%20V5.0%20Debug.exe')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/applicationpoller.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/config.ini')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/constructinterpretedlog.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/emslifecycle.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/flaskappui.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/imeinterpreter.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/logprocessinglibrary.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/update.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/subgraph.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/win32app.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/logging keyword table.json')
    # url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/update.exe')


def hot_update_github_links():
    url_list.clear()
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/applicationpoller.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/config.ini')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/constructinterpretedlog.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/emslifecycle.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/flaskappui.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/imeinterpreter.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/logprocessinglibrary.py')
    # url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/update.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/subgraph.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/win32app.py')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/logging keyword table.json')
    url_list.append('https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/update.exe')


def download_file(i, total_sizes, downloaded_sizes, completed_downloads, lock):
    url = url_list[i]
    filename = url.split("/")[-1].replace('%20',' ')
    response = requests.get(url, stream=True)
    total = response.headers.get('content-length')
    # print("a: " + total)
    if total is not None:
        total = int(total)
        total_sizes[i] = total
        # print(total_sizes)
    downloaded = 0

    # print(completed_downloads)

    # time.sleep(3)
    with open(filename, 'wb') as f:
        for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
            f.write(data)
            downloaded += len(data)
            downloaded_sizes[i] = downloaded
            if total is not None:
                overall_downloaded = sum(downloaded_sizes)
                overall_total = sum(total_sizes)
                progress_percent = 100 * overall_downloaded / overall_total
                download_progress.set(progress_percent)
                set_title(f"Download Progress: {progress_percent:.2f}%")
    if downloaded >= total:
        with lock:  # make the increment operation thread-safe
            completed_downloads[0] += 1
            #print(str(i))
            #print(completed_downloads)
        if completed_downloads[0] == len(url_list):  # all downloads complete
            set_title(f"Download Progress: 100%")
            time.sleep(1.5)
            set_title(f"Update Success! You can close the window!")
            time.sleep(10)
            # root.destroy()  # close the application


def get_total_size(total_sizes):
    for i in range(len(url_list)):
        url = url_list[i]
        response = requests.get(url, stream=True)
        total = response.headers.get('content-length')
        if total is not None:
            total = int(total)
            total_sizes[i] = total


def hot_update():
    hot_update_github_links()
    total_sizes = [0] * len(url_list)
    get_total_size(total_sizes)
    downloaded_sizes = [0] * len(url_list)
    completed_downloads = [0]  # list used to make this variable mutable inside the threads
    lock = Lock()  # a lock for thread-safe operation on completed_downloads

    def start_thread(i):
        this_thread = Thread(target=download_file, args=(i, total_sizes, downloaded_sizes, completed_downloads, lock))
        this_thread.start()
        thread_list.append(this_thread)

    for i in range(len(url_list)):
        start_thread(i)

    for i in range(len(thread_list)):
        thread_list[i].join()

    return True


def cold_update():
    cold_update_github_links()
    download_progress.set(0)

    total_sizes = [0]*len(url_list)
    get_total_size(total_sizes)
    downloaded_sizes = [0]*len(url_list)
    completed_downloads = [0]  # list used to make this variable mutable inside the threads
    lock = Lock() # a lock for thread-safe operation on completed_downloads

    def start_thread(i):
        this_thread = Thread(target=download_file, args=(i, total_sizes, downloaded_sizes, completed_downloads, lock))
        this_thread.start()
        thread_list.append(this_thread)

    for i in range(len(url_list)):
        root.after(400+100*i, start_thread, i)


def set_title(text=""):
    root.title(f"{text}")


if __name__ == '__main__':
    root = tk.Tk()
    root.title(f"Download Progress: 0%")
    download_progress = tk.DoubleVar()
    percent = tk.StringVar()

    frame = tk.Frame(root)
    frame.pack()

    progress_bar = ttk.Progressbar(frame, length=500, mode='determinate', variable=download_progress, maximum=100)
    progress_bar.grid(row=0, column=0)

    # Commented out to remove percentage inside the progress bar
    # percent_label = tk.Label(frame, textvariable=percent)
    # percent_label.grid(row=0, column=0)

    ttk.Label(root, text="Updating Program").pack()

    root.after(100, cold_update)  # Delay start

    root.mainloop()
