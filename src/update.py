import random

import requests
import tkinter as tk
from tkinter import ttk
from threading import Thread
from threading import Lock
import configparser
import time
import sys
from PyQt5.QtWidgets import *
url_list = []
thread_list = []
download_progress = 0
global appwindow
appwindow = None


def cold_update_prepare_github_links():
    url_list.clear()
    config_local = configparser.ConfigParser()
    config_local.read('config.ini')
    download_items = config_local.options('UPDATELINKS')
    # Update everything except update.exe
    download_items.remove('updateexe')
    download_items.remove('updatepy')
    for each_update_item in download_items:
        each_url = config_local['UPDATELINKS'][each_update_item].replace(' ', '%20')
        url_list.append(each_url)


def hot_update_prepare_github_links():
    url_list.clear()
    config_local = configparser.ConfigParser()
    config_local.read('config.ini')
    download_items = config_local.options('UPDATELINKS')
    # Update everything except update.py, mainexe,
    download_items.remove('updateexe')
    for each_update_item in download_items:
        each_url = config_local['UPDATELINKS'][each_update_item].replace(' ', '%20')
        url_list.append(each_url)


def download_file(i, total_sizes, downloaded_sizes, completed_downloads, lock):
    url = url_list[i]
    filename = url.split("/src/")[-1]
    url = url.replace(' ', '%20')
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length'))
    overall_total = sum(total_sizes)
    # # print("a: " + total)
    # if total is not None:
    #     total = int(total)
    #     total_sizes[i] = total
        # print(total_sizes)
    downloaded = 0

    # print(completed_downloads)
    if total is not None:
        # time.sleep(3)
        with open(filename, 'wb') as f:
            for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
                f.write(data)
                downloaded += len(data)
                downloaded_sizes[i] = downloaded
                overall_downloaded = sum(downloaded_sizes)
                progress_percent = 100 * overall_downloaded // overall_total
                with lock:
                    download_progress.setValue(progress_percent)
    if downloaded >= total:
        with lock:  # make the increment operation thread-safe
            completed_downloads[0] += 1
            #print(str(i))
            #print(completed_downloads)
        if completed_downloads[0] == len(url_list):  # all downloads complete
            download_progress.setValue(100)
            time.sleep(3)

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
    hot_update_prepare_github_links()
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
    cold_update_prepare_github_links()
    download_progress.setValue(0)

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
        time.sleep(0.3)
        start_thread(i)
    for i in range(len(thread_list)):
        thread_list[i].join()
    return True


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Updating IME Interpreter V5.0")
        self.setGeometry(800, 600, 800, 250)

        # Create a progress bar
        self.progress = QProgressBar(self)
        self.progress.setGeometry(30, 20, 750, 35)
        global download_progress
        download_progress = self.progress

        # Create a button to start the progress
        self.textlabel = QLabel(self)
        self.textlabel.setText("Updating.....")
        self.textlabel.setGeometry(30, 60, 800, 35)
        # self.btn = QPushButton("Start Progress", self)
        # self.btn.setGeometry(30, 80, 100, 30)
        # self.btn.clicked.connect(self.start_progress)

    def start_progress(self):
        # Simulate progress (you can replace this with your actual logic)
        for i in range(101):
            self.progress.setValue(i)
            QApplication.processEvents()  # Update the UI


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    appwindow = window
    window.show()
    cold_update()
    window.textlabel.setText("Update Completed. You can close the window.")
    time.sleep(10)
    sys.exit(app.exec_())
