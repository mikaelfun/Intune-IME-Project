import sys
import threading

import requests
from flask import Flask, render_template, request, jsonify
from imeinterpreter import *
import configparser
from selfupdate import update
import update
import webbrowser


def update_selfupdater():
    url = 'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/update.exe'
    filename = url.split("/")[-1].replace('%20', ' ')
    response = requests.get(url, stream=True)
    total = response.headers.get('content-length')

    with open(filename, 'wb') as f:
        if total is None:
            f.write(response.content)
        else:
            downloaded = 0
            total = int(total)
            for data in response.iter_content(chunk_size=max(int(total / 1000), 1024 * 1024)):
                downloaded += len(data)
                f.write(data)


def thread_job():
    try:
        update_selfupdater()
        print("Update update.exe Success!")
    except:
        print("Unable to update update.exe!")


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')


# New route for checking update availability
@app.route('/check_update')
def check_update():
    # Call your Python function (e.g., check_update_available())
    # Replace this with your actual logic
    update_available = False  # Assume it's True for demonstration
    try:
        config_local = configparser.ConfigParser()
        config_local.read('config.ini')
        version_local = config_local['DEFAULT']['version']

        url = 'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/config.ini'
        response = requests.get(url)
        config_github = configparser.ConfigParser()
        config_as_string = response.content.decode('utf-8')
        config_github.read_string(config_as_string)
        version_github = config_github['DEFAULT']['version']

        # print(version_local)
        # print(version_github)
        if version_github != version_local:
            update_available = True

    except:
        print("Unable to read local version from config.ini!")

    # Return the result as JSON
    if update_available:
        # call update
        result = update.hot_update()
        if result:
            return "Updated"
        else:
            return "Update Failed"
    else:
        return "Up to date"


@app.route('/analyze', methods=['POST'])
def analyze():
    folder_path = request.form.get('IMEFolderPath')
    logModeOn = request.form.get('logModeOn')
    full_log_mode = False
    # print(logModeOn)
    if logModeOn == "false":
        full_log_mode = False
    elif logModeOn == "true":
        full_log_mode = True
    # print(full_log_mode)
    a = ImeInterpreter(folder_path)
    result = a.generate_ime_interpreter_log_output_webui(full_log_mode)

    return result


if __name__ == '__main__':
    args = sys.argv
    # t = threading.Thread(target=thread_job)
    # t.start()

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
            outfile.write(a.generate_ime_interpreter_log_output_webui(full_log_switch))
        print("Log output successful!")
        sys.exit("Log output successful!")
    else:
        app.run()