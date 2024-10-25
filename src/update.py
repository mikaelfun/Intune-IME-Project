import os
import shutil
import subprocess
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
main_program_path = os.path.join(os.getcwd(), "IME Interpreter V5.0.exe")

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


def download_file_via_url(url, timeout=180):
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


def hot_update_singlethread():
    try:
        config_local = configparser.ConfigParser()
        config_local.read('config.ini')
        config_local.set('APPMETA', 'isupdating', 'True')
        # Save the changes
        print("Saving config.ini to isupdating True")
        with open('config.ini', 'w') as config_file:
            config_local.write(config_file)
            config_file.flush()  # Flush the changes
            config_file.close()  # Close the file
        print("Saved config.ini to isupdating True")
    except:
        print("Unable to read local version from config.ini!")
        return False
    logging.info("Hot - Update prepare update links..")
    hot_update_prepare_github_links()
    logging.info("Hot - Update started")
    print("Hot Update begins")
    temp_download_path = "temp"
    if not os.path.exists(temp_download_path):
        os.makedirs(temp_download_path)
    for i in range(len(url_list)):
        url = url_list[i]
        update_timeout = int(config_local['APPMETA']['updatetimeout'])
        result = download_file_via_url(url, timeout=update_timeout)
        if not result:
            os.removedirs(temp_download_path)
            print("Hot Update failed")
            logging.error("Hot - Update failed.")

            config_local.set('APPMETA', 'isupdating', 'False')
            # Save the changes
            print("Saving config.ini to isupdating False")
            with open('config.ini', 'w') as config_file:
                config_local.write(config_file)
                config_file.flush()  # Flush the changes
                config_file.close()  # Close the file
            print("Saved config.ini to isupdating False")
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


def restart_program():
    print("Restarting program...")
    # print(main_program_path)
    subprocess.run([main_program_path])
    # os.execl(python, python, main_program_path)


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

    def delayed_exit(self):
        time.sleep(3)
        sys.exit()

    def cold_update_singlethread(self):
        # appwindow.firstline.setText("Initializing update links..")
        self.update_firstline_signal.emit("Initializing update links..")
        cold_update_prepare_github_links()
        # appwindow.progress.setValue(0)
        self.update_progress_signal.emit(0)
        total_progress_bars = len(url_list)
        # Grey out button to prevent incomplete update download
        self.update_button_signal.emit(False)

        # temp_download_path = "temp"
        # if not os.path.exists(temp_download_path):
        #     os.makedirs(temp_download_path)
        #
        # for i in range(len(url_list)):
        #     self.update_progress_signal.emit(((i+1))*100//total_progress_bars)
        #     url = url_list[i]
        #     self.download_file_via_url(url)
        #
        # try:
        #     shutil.copytree(temp_download_path, '.\\', symlinks=False, ignore=None, ignore_dangling_symlinks=False,
        #                     dirs_exist_ok=True)
        #     print(f"Successfully copied {temp_download_path} to root")
        #     shutil.rmtree(temp_download_path, ignore_errors=True)
        # except Exception as e:
        #     print(f"Error copying {temp_download_path}: {e}")
        # print("Cold Update finishes")
        # logging.info("Cold - Update finished.")

        # UnGrey out button to prevent incomplete update download
        self.update_button_signal.emit(True)
        # appwindow.progress.setValue(100)
        self.update_progress_signal.emit(100)
        self.update_firstline_signal.emit("Update Completed. You can close the window.")
        self.update_secondline_signal.emit("")
        restart_program()
        exit_thread = Thread(target=self.delayed_exit)
        exit_thread.start()

    def download_file_via_url(self, url):
        filename = url.split("/src/")[-1].replace('%20', ' ')

        temp_download_file = "temp" + "\\" + filename
        parent_directory = os.path.dirname(temp_download_file)
        if not os.path.exists(parent_directory):
            os.makedirs(parent_directory)

        # appwindow.firstline.setText("Downloading..." + filename)
        self.update_firstline_signal.emit("Downloading...")
        self.update_secondline_signal.emit(filename)
        logging.info("Downloading..." + filename)
        response = requests.get(url, stream=True)
        total = int(response.headers.get('content-length'))
        with open(temp_download_file, 'wb') as f:
            for data in response.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                f.write(data)
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