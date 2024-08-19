import os
from datetime import datetime
import logging
import requests
from threading import Thread
from threading import Lock
import configparser
import time
import sys

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QObject, pyqtSignal, QThread

url_list = []
thread_list = []
global overall_downloaded
overall_downloaded = 0
global total_sizes
total_sizes = 0

# 日志文件
folder_path = "logs"
if not os.path.exists(folder_path):
    os.makedirs(folder_path)

logfilename = "logs\\update_log_" + datetime.now().strftime(
    "%Y-%m-%d") + ".txt"  # Setting the filename from current date and time
logging.basicConfig(filename=logfilename, filemode='a',
                    format="%(asctime)s, %(msecs)d %(name)s %(levelname)s "
                           "[ %(filename)s-%(module)s-%(lineno)d ]  : %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    level=logging.INFO)


def cold_update_prepare_github_links():
    url_list.clear()
    config_local = configparser.ConfigParser()
    config_local.read('config.ini')
    download_items = config_local.options('UPDATELINKS')
    # Update everything except update.exe
    download_items.remove('updateexe')
    # download_items.remove('updatepy')
    for each_update_item in download_items:
        each_url = config_local['UPDATELINKS'][each_update_item].replace(' ', '%20')
        url_list.append(each_url)


def hot_update_prepare_github_links():
    url_list.clear()
    config_local = configparser.ConfigParser()
    config_local.read('config.ini')
    download_items = config_local.options('UPDATELINKS')
    # Update everything except update.py, mainexe,
    download_items.remove('updatepy')
    download_items.remove('mainexe')
    for each_update_item in download_items:
        each_url = config_local['UPDATELINKS'][each_update_item].replace(' ', '%20')
        url_list.append(each_url)


def download_file_multithread(i, total_sizes_list, downloaded_sizes, completed_downloads, lock):
    url = url_list[i]
    filename = url.split("/src/")[-1].replace('%20', ' ')

    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length'))
    overall_total = sum(total_sizes_list)
    # # print("a: " + total)
    # if total is not None:
    #     total = int(total)
    #     total_sizes_list[i] = total
        # print(total_sizes_list)
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
                    appwindow.progress.setValue(progress_percent)
    if downloaded >= total:
        with lock:  # make the increment operation thread-safe
            completed_downloads[0] += 1
            #print(str(i))
            #print(completed_downloads)
        if completed_downloads[0] == len(url_list):  # all downloads complete
            appwindow.progress.setValue(100)
            time.sleep(3)

            # root.destroy()  # close the application


def download_file_via_url(url):
    filename = url.split("/src/")[-1].replace('%20', ' ')
    appwindow.firstline.setText("Downloading..." + filename)
    logging.info("Downloading..." + filename)
    response = requests.get(url, stream=True)
    total = int(response.headers.get('content-length'))
    with open(filename, 'wb') as f:
        for data in response.iter_content(chunk_size=max(int(total/1000), 1024*1024)):
            f.write(data)
            global overall_downloaded, total_sizes
            overall_downloaded += len(data)
            progress_percent = 100 * overall_downloaded // total_sizes
            appwindow.progress.setValue(progress_percent)
            appwindow.secondline.setText("Total file size: \n" + str(overall_downloaded) + "/" + str(total_sizes))
    logging.info("Downloaded..." + filename)


def get_total_size(total_sizes_list):
    for i in range(len(url_list)):
        url = url_list[i]
        response = requests.get(url, stream=True)
        total = response.headers.get('content-length')
        if total is not None:
            total = int(total)
            total_sizes_list[i] = total


def hot_update_multithread():
    hot_update_prepare_github_links()
    total_sizes_list = [0] * len(url_list)
    get_total_size(total_sizes_list)
    downloaded_sizes = [0] * len(url_list)
    completed_downloads = [0]  # list used to make this variable mutable inside the threads
    lock = Lock()  # a lock for thread-safe operation on completed_downloads

    def start_thread(i):
        this_thread = Thread(target=download_file_multithread, args=(i, total_sizes_list, downloaded_sizes, completed_downloads, lock))
        this_thread.start()
        thread_list.append(this_thread)

    for i in range(len(url_list)):
        start_thread(i)

    for i in range(len(thread_list)):
        thread_list[i].join()

    return True


def hot_update_singlethread():
    hot_update_prepare_github_links()
    appwindow.progress.setValue(0)
    logging.info("Hot - Calculating file size to download..")
    for i in range(len(url_list)):
        url = url_list[i]
        response = requests.get(url, stream=True)
        current_total = response.headers.get('content-length')
        if current_total is not None:
            current_total = int(current_total)
            global total_sizes
            total_sizes = total_sizes + current_total
    logging.info("Hot - Calculated file size to download..")

    for i in range(len(url_list)):
        url = url_list[i]
        download_file_via_url(url)

    return True


def cold_update_singlethread():
    appwindow.firstline.setText("Initializing update links..")
    cold_update_prepare_github_links()
    appwindow.progress.setValue(0)
    appwindow.firstline.setText("Calculating file size to download..")

    logging.info("Cold - Calculating file size to download..")
    for i in range(len(url_list)):
        url = url_list[i]
        filename = url.split("/src/")[-1].replace('%20', ' ')
        appwindow.secondline.setText("Fetching size for: " + filename)
        response = requests.get(url, stream=True)
        current_total = response.headers.get('content-length')
        if current_total is not None:
            current_total = int(current_total)
            global total_sizes
            total_sizes = total_sizes + current_total

    logging.info("Cold - Calculated file size to download..")
    appwindow.secondline.setText("Total file size: \n" + "0/" + str(total_sizes))

    for i in range(len(url_list)):
        url = url_list[i]
        download_file_via_url(url)

    appwindow.progress.setValue(100)
    appwindow.secondline.setText("Total file size: \n" + str(total_sizes) + "/" + str(total_sizes))
    appwindow.firstline.setText("Update Completed. You can close the window.")
    return True


def cold_update_multithread():
    cold_update_prepare_github_links()
    appwindow.progress.setValue(0)
    total_sizes_list = [0]*len(url_list)
    get_total_size(total_sizes_list)
    downloaded_sizes = [0]*len(url_list)
    completed_downloads = [0]  # list used to make this variable mutable inside the threads
    lock = Lock() # a lock for thread-safe operation on completed_downloads

    def start_thread(i):
        this_thread = Thread(target=download_file_multithread, args=(i, total_sizes_list, downloaded_sizes, completed_downloads, lock))
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
        self.setWindowTitle("IME Interpreter V5.0 Updater")
        self.setGeometry(800, 600, 800, 250)

        # Create a progress bar
        self.progress = QProgressBar(self)
        self.progress.setGeometry(30, 20, 750, 35)

        custom_font = QFont("Arial", 8)#QFont.Bold)
        # Create a button to start the progress
        self.firstline = QLabel(self)
        self.firstline.setFont(custom_font)
        self.firstline.setText("Update in progress..")
        self.firstline.setGeometry(30, 60, 800, 60)
        self.secondline = QLabel(self)
        self.secondline.setFont(custom_font)
        self.secondline.setText("")
        self.secondline.setGeometry(30, 110, 800, 60)
        self.btn = QPushButton("CLOSE", self)
        self.btn.setGeometry(350, 180, 120, 60)
        self.btn.clicked.connect(self.close_app)

    def handle_progress_update(self, progress):
        # Update your UI based on the progress value
        self.progress.setValue(progress)

    def handle_firstline_update(self, result):
        # Update your UI based on the progress value
        self.firstline.setText(result)

    def handle_secondline_update(self, result):
        # Update your UI based on the progress value
        self.secondline.setText(result)

    def handle_close_button_status(self, state):
        # Disable the button (make it grayed out)
        self.btn.setEnabled(state)

    def close_app(self):
        sys.exit()


class ColdUpdateThread(QThread):
    # Define any signals you need (if applicable)
    update_progress_signal = pyqtSignal(int)
    update_firstline_signal = pyqtSignal(str)
    update_secondline_signal = pyqtSignal(str)
    update_button_signal = pyqtSignal(bool)

    def run(self):
        # Your thread logic here
        self.cold_update_singlethread()

    def cold_update_singlethread(self):
        # appwindow.firstline.setText("Initializing update links..")
        self.update_firstline_signal.emit("Initializing update links..")
        cold_update_prepare_github_links()
        # appwindow.progress.setValue(0)
        self.update_progress_signal.emit(0)
        # appwindow.firstline.setText("Calculating file size to download..")
        self.update_firstline_signal.emit("Calculating file size to download..")
        time.sleep(2)
        total_progress_bars = len(url_list) * 2
        logging.info("Cold - Calculating file size to download..")
        for i in range(len(url_list)):
            url = url_list[i]
            filename = url.split("/src/")[-1].replace('%20', ' ')
            # appwindow.secondline.setText("Fetching size for: " + filename)
            self.update_secondline_signal.emit("Fetching size for: " + filename)
            self.update_progress_signal.emit((i+1)*100//total_progress_bars)
            response = requests.get(url, stream=True)
            current_total = response.headers.get('content-length')
            if current_total is not None:
                current_total = int(current_total)
                global total_sizes
                total_sizes = total_sizes + current_total

        logging.info("Cold - Calculated file size to download..")
        # appwindow.secondline.setText("Total file size: \n" + "0/" + str(total_sizes))
        self.update_secondline_signal.emit("Total file size: \n" + "0/" + str(total_sizes))

        # Grey out button to prevent incomplete update download
        self.update_button_signal.emit(False)
        for i in range(len(url_list)):
            self.update_progress_signal.emit((len(url_list) + (i+1))*100//total_progress_bars)
            url = url_list[i]
            self.download_file_via_url(url)

        # UnGrey out button to prevent incomplete update download
        self.update_button_signal.emit(True)
        # appwindow.progress.setValue(100)
        self.update_progress_signal.emit(100)
        # appwindow.secondline.setText("Total file size: \n" + str(total_sizes) + "/" + str(total_sizes))
        # self.update_secondline_signal.emit("Total file size: \n" + str(total_sizes) + "/" + str(total_sizes))
        # appwindow.firstline.setText("Update Completed. You can close the window.")
        self.update_firstline_signal.emit("Update Completed. You can close the window.")
        self.update_secondline_signal.emit("")

    def download_file_via_url(self, url):
        filename = url.split("/src/")[-1].replace('%20', ' ')
        # appwindow.firstline.setText("Downloading..." + filename)
        self.update_firstline_signal.emit("Downloading...")
        self.update_secondline_signal.emit(filename)
        logging.info("Downloading..." + filename)
        response = requests.get(url, stream=True)
        total = int(response.headers.get('content-length'))
        with open(filename, 'wb') as f:
            for data in response.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                f.write(data)
                global overall_downloaded, total_sizes
                overall_downloaded += len(data)
                # progress_percent = 100 * overall_downloaded // total_sizes
                # appwindow.progress.setValue(progress_percent)
                # appwindow.secondline.setText("Total file size: \n" + str(overall_downloaded) + "/" + str(total_sizes))
                # self.update_secondline_signal.emit("Total file size: \n" + str(overall_downloaded) + "/" + str(total_sizes))
        logging.info("Downloaded..." + filename)


if __name__ == '__main__':
    updateapp = QApplication(sys.argv)
    appwindow = MyWindow()
    appwindow.show()

    update_thread = ColdUpdateThread()
    update_thread.update_progress_signal.connect(appwindow.handle_progress_update)
    update_thread.update_firstline_signal.connect(appwindow.handle_firstline_update)
    update_thread.update_secondline_signal.connect(appwindow.handle_secondline_update)
    update_thread.update_button_signal.connect(appwindow.handle_close_button_status)
    update_thread.start()  # Start the thread

    # update_thread = Thread(target=cold_update_singlethread)
    # update_thread.start()
    updateapp.exec_()
