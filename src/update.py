import os
import shutil
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
    # download_items.remove('updateexe')
    for each_update_item in download_items:
        each_url = config_local['UPDATELINKS'][each_update_item].replace(' ', '%20')
        url_list.append(each_url)


def download_file_via_url(url, timeout=120):
    try:
        filename = url.split("/src/")[-1].replace('%20', ' ')
        temp_download_file = "temp" + "\\" + filename
        parent_directory = os.path.dirname(temp_download_file)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)
        logging.info("Downloading..." + filename)
        start_time = time.time()
        response = requests.get(url, stream=True, timeout=timeout)
        if response.status_code == 200:
            total = int(response.headers.get('content-length'))
            with open(temp_download_file, 'wb') as f:
                for data in response.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                    f.write(data)
            if time.time() - start_time > timeout:
                raise requests.Timeout("Timeout exceeded!")
            logging.info("Downloaded..." + filename)
            return True
        else:
            print(f"Failed to download: {url} (Status code: {response.status_code})")
            logging.error(f"Failed to download: {url} (Status code: {response.status_code})")
            return False
    except requests.Timeout:
        print(f"Timeout while downloading: {url}")
        logging.error(f"Timeout while downloading: {url}")
        return False



def get_total_size(total_sizes_list):
    for i in range(len(url_list)):
        url = url_list[i]
        response = requests.get(url, stream=True)
        total = response.headers.get('content-length')
        if total is not None:
            total = int(total)
            total_sizes_list[i] = total


def hot_update_singlethread():
    logging.info("Hot - Update prepare update links..")
    hot_update_prepare_github_links()
    logging.info("Hot - Update started")
    print("Hot Update begins")
    temp_download_path = "temp"
    if not os.path.exists(temp_download_path):
        os.makedirs(temp_download_path)
    for i in range(len(url_list)):
        url = url_list[i]
        result = download_file_via_url(url, timeout=120)
        if not result:
            os.removedirs(temp_download_path)
            print("Hot Update failed")
            logging.error("Hot - Update failed.")
            return False
    try:
        shutil.copytree(temp_download_path, '.\\', symlinks=False, ignore=None, ignore_dangling_symlinks=False, dirs_exist_ok=True)
        print(f"Successfully copied {temp_download_path} to root")
        shutil.rmtree(temp_download_path, ignore_errors=True)
    except Exception as e:
        print(f"Error copying {temp_download_path}: {e}")
    print("Hot Update finishes")
    logging.info("Hot - Update finished.")
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
    update_thread.start()

    updateapp.exec_()