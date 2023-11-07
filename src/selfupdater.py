import requests


def download_file(url, filename):
    # Send a HTTP request to the URL
    r = requests.get(url, allow_redirects=True)

    # Write the content of the request to a file
    open(filename, 'wb').write(r.content)


def update_pyd_and_json_from_github():
    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/logging%20keyword%20table.json',
        'logging keyword table.json')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/imeinterpreter.cp311-win_amd64.pyd',
        'imeinterpreter.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/constructinterpretedlog.cp311-win_amd64.pyd',
        'constructinterpretedlog.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/logprocessinglibrary.cp311-win_amd64.pyd',
        'logprocessinglibrary.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/emslifecycle.cp311-win_amd64.pyd',
        'emslifecycle.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/applicationpoller.cp311-win_amd64.pyd',
        'applicationpoller.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/subgraph.cp311-win_amd64.pyd',
        'subgraph.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/tkinterui.cp311-win_amd64.pyd',
        'tkinterui.cp311-win_amd64.pyd')

    download_file(
        'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/win32app.cp311-win_amd64.pyd',
        'win32app.cp311-win_amd64.pyd')
