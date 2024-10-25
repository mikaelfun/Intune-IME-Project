import shutil
import sys
import threading
import time

import requests
import os
from flaskappui import *
import configparser


def update_selfupdater():
    try:
        config_local = configparser.ConfigParser()
        config_local.read('config.ini')

        version_local = config_local['APPMETA']['version']

        config_url = config_local['UPDATELINKS']['configini']
        try:
            response = requests.get(config_url)
        except:
            # without VPN, cannot get github link. Expected
            print("Failing to connect to GitHub repo. Check your VPN connection. Skipping self update.")
            return None
        config_github = configparser.ConfigParser()
        config_as_string = response.content.decode('utf-8')
        config_github.read_string(config_as_string)
        version_github = config_github['APPMETA']['version']

        update_url_local = config_local['UPDATELINKS']['updateexe']
    except:
        print("E1. Error reading config.ini!! Run update.exe to fix!")
        return None

    # if version_github != version_local:
    dest_filename = update_url_local.split("/")[-1].replace('%20', ' ')
    filename = dest_filename.replace('.', '_tmp.')
    response = requests.get(update_url_local, stream=True)
    total = response.headers.get('content-length')
    print("Updating update.exe in GitHub")
    if total is None:
        print("Unknown file size of update.exe in GitHub")
        return None
    else:
        if response.status_code == 404:
            print("Download link for update.exe not found in GitHub")
        elif response.status_code == 200:
            with open(filename, 'wb') as f:
                downloaded = 0
                total = int(total)
                for data in response.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                    downloaded += len(data)
                    f.write(data)
            shutil.move(filename, dest_filename)
            print("Update update.exe Success!")
            return True
        else:
            print("Unknown status code: " + response.status_code + " Not updating update.exe")
            return None
    # else:
    #     print("No need to update update.exe since no new version found")


def update_thread_job():
    # delay 10 seconds to update update.exe
    time.sleep(10)
    if update_selfupdater():
        pass
    else:
        print("Unable to update update.exe!")


def cleanup():
    print("Cleaning up before exit...")
    os._exit(0)


if __name__ == '__main__':
    args = sys.argv
    t = threading.Thread(target=update_thread_job)
    t.start()

    if len(args) > 1:
        path_to_ime_log_folder = args[1]
        if not os.path.exists(path_to_ime_log_folder):
            print('''Invalid argument! "path_to_ime_log_folder" does not exist!''')
            sys.exit('''Invalid argument! "path_to_ime_log_folder" does not exist!''')

        if len(args) <= 2 or len(args) >= 5:
            print(
                '''Invalid argument! Please follow "IME_Interpreter_UI 5.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')
            sys.exit(
                '''Invalid argument! Please follow "IME_Interpreter_UI 5.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')

        path_to_output_file = args[2]
        full_log_switch = False
        if len(args) == 4:
            if args[3] == "FULL":
                full_log_switch = True
            else:
                print(
                    '''Invalid argument! Please follow "IME_Interpreter_UI 5.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')
                sys.exit(
                    '''Invalid argument! Please follow "IME_Interpreter_UI 5.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')

        from imeinterpreter import *

        a = ImeInterpreter(path_to_ime_log_folder)
        with open(path_to_output_file, 'w') as outfile:
            # Write some text to the file
            outfile.write(a.generate_win32_interpreter_log_output_webui(full_log_switch))
        print("Log output successful!")
        sys.exit("Log output successful!")
    else:
        try:
            config_local = configparser.ConfigParser()
            config_local.read('config.ini')
            port_local = int((config_local['APPMETA']['appurl']).split(':')[-1].replace('/', ''))
            debug_str_local = (config_local['APPMETA']['debug'])
            if debug_str_local == 'True':
                debug_on = True
            else:
                debug_on = False

            # debug_on = True
            open_browser()
            ime_interpreter_app.run(port=port_local, debug=debug_on)
            exit(0)
        except:
            open_browser()
            ime_interpreter_app.run(port=5000, debug=True)
            print("E2. Error reading config.ini!! Run update.exe to fix!")

# if __name__ == '__main__':
#     from imeinterpreter import *
#
#     path_to_ime_log_folder = r"D:\Kun\Downloads\IME test logs\mdmdiagreport"
#     a = ImeInterpreter(path_to_ime_log_folder)
#     #print(a.generate_powershell_interpreter_log_output_webui())
#     print(a.generate_win32_interpreter_log_output_webui())
#     #print(a.generate_remediation_interpreter_log_output_webui())
