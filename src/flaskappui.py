import webbrowser
import requests
from flask import Flask, render_template, request, jsonify
from imeinterpreter import *
import configparser
from selfupdate import update
import update


ime_interpreter_app = Flask(__name__)


@ime_interpreter_app.route('/')
def home():
    return render_template('index.html')


def open_browser():
    try:
        config_local = configparser.ConfigParser()
        config_local.read('config.ini')
        app_url_local = config_local['DEFAULT']['appurl']
    except:
        print("Error reading config.ini!! Run update.exe to fix!")
        return None
    webbrowser.open_new(app_url_local)


# New route for checking update availability
@ime_interpreter_app.route('/check_update')
def check_update():
    # Call your Python function (e.g., check_update_available())
    # Replace this with your actual logic
    update_available = False  # Assume it's True for demonstration
    try:
        config_local = configparser.ConfigParser()
        config_local.read('config.ini')
        version_local = config_local['DEFAULT']['version']

        config_url = config_local['UPDATELINKS']['configini']
        response = requests.get(config_url)
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


@ime_interpreter_app.route('/analyze', methods=['POST'])
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
    if (os.path.isdir(folder_path)):
        a = ImeInterpreter(folder_path)
        result = a.generate_ime_interpreter_log_output_webui(full_log_mode)

        return result
    else:
        return "Folder Not Found! Please check the folder path is valid."


@ime_interpreter_app.route('/getversion')
def get_version():
    try:
        config_local = configparser.ConfigParser()
        config_local.read('config.ini')
        version_local = config_local['DEFAULT']['version']
    except:
        print("Error reading config.ini!! Run update.exe to fix!")
        version_local = "v5.0.0"
    return version_local

