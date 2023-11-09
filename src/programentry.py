"""
Main input should be a folder path
Folder contains all IME logs such as
1. IntuneManagementExtension.log
2. IntuneManagementExtension-20230323-114128.log
3. IntuneManagementExtension-yyyymmdd-xxxxxx.log

Step 1:
Concatenate all log file into one text variable
Step 2:
Separate whole log into each EMS agent start interval.
a. Each interval between EMS agent starts and EMS agent stops represent a full life cycle without powering
down/stopping IME service.
b. Determine whether it's IME service restart or reboot based on time spent to start EMS agent.
Normally service restart will take less than 5 seconds. Reboot will take more than 1 minute.
Step 3:
Inside each EMS agent lifecycle, separate into Application poller sessions.
Determine if it's required app session or available app session. Required apps triggered by service automatically
every 1 hour. Available app triggerd by clicking on company portal install.
Step 3:
Process each Application Poller sessions.
a. Check throttling count. throttle limit 25 every 1 hour(for IME agent cycle)
<![LOG[Successfully updated throttling info. workload AgentCheckIn, currentCnt = 25
Thottle limit works for required app check in, powershell check in, inventory check in
Get Session metadata. Get policies, retrieve current session apps to be processed after evaluating assignment +
dependency
b. V3Processor starts processing all Subgraphs (Subgraph is a group of apps with dependency/supersedence/standalone,
it can be just 1 app in the subgraph)
Subgraph processing has overall re-eval time. If it expires, it will update the re-eval time to current after processing
all subgraphs. If not it will do nothing
Each subgraph has its own re-eval time, if it's not expired, it will not process apps in the subgraph even when they are
expired.


c. For each subgraph
    i. Check previous subgraph reevaluation time value and get subgraph hash key,
    if subgraph eval not expired, it will not process the subgraph
    if subgraph eval expired, apps' grs expired, it will process the subgraph detection only for all apps.
    ii. GRS eval, GRSManager, based on GRS, if Subgraph app is not expired, go to 4.c
    iii. ActionProcessor will run detection and applicability for all apps in subgraph
        1) DetectionActionHandler detects each app in subgraph
            a) WinGetAppDetectionExecutor
            b) Normal Win32 detection
        2) ApplicabilityActionHandler checks applicability(basic) each app in subgraph
            a) WinGetAppApplicabilityExecutor
            b) Normal Win32 applicability check
        3) ActionProcessor summarize each app effective intent, detection, appilcability, reboot status, GRS
        4) ActionProcessor check if action required for each app, if need to install
            a) ExecutionActionHandler triggers
                i) WinGetAppExecutionExecutor
            b) start to Download,
            c) detect,
                i) WinGetAppDetectionExecutor
            d) install,
                i) WinGetAppExecutionExecutor
            e) detect by Win32 processing(skipped), detect by DetectionActionHandler
                i) WinGetAppDetectionExecutor
        5) ActionProcessor summarizes all apps in subgraph, done. Subgraph check-in is 8 hours
    iv. If current subgraph has hard reboot, it will stop processing rest subgraphs and reboot first.
d. V3Processor done
e. GRSManager sets GRS time for each app to current time
f. Application poller stops


note:
Currently only Win32 apps support dependency, WUFB UWP apps do not support dependency.
So we can simplify the subgraph processing for dependent apps to use Win32 processing logic directly.

Later when Intune supports MSFB Win32 app, it may also support dependency then. Need to adapt code later then.




"""
import sys
import os
from tkinterui import *
import tkinter
from tkinter import ttk
from tkinter import filedialog
import json
import requests
import threading
import sys


def thread_job():
    try:
        update_selfupdater()
        print("Update selfupdater.exe Success!")
    except:
        print("Unable to update selfupdater.exe!")


def update_selfupdater():
    url = 'https://raw.githubusercontent.com/mikaelfun/Intune-IME-Project/main/src/selfupdater.exe'
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


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-30-04-21-47"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-27-03-20-10"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-17-03-50-20"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-24-00-54-21"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-24-04-02-41"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-23-06-06-17"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-16-07-45-17"
    # test_log_folder = r"D:\Kun\Downloads\IME test logs\mdmlogs-2023-10-17-13-53-48"
    # a = ImeInterpreter(test_log_folder)
    # print(a.generate_ime_interpreter_log_output(False))

    # update_pyd_and_json_from_github()

    args = sys.argv
    t = threading.Thread(target=thread_job)
    t.start()

    if len(args) > 1:
        path_to_ime_log_folder = args[1]
        if not os.path.exists(path_to_ime_log_folder):
            print('''Invalid argument! "path_to_ime_log_folder" does not exist!''')
            sys.exit('''Invalid argument! "path_to_ime_log_folder" does not exist!''')

        if len(args) <= 2 or len(args) >= 5:
            print(
                '''Invalid argument! Please follow "IME_Interpreter_UI 4.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')
            sys.exit(
                '''Invalid argument! Please follow "IME_Interpreter_UI 4.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')

        path_to_output_file = args[2]
        full_log_switch = False
        if len(args) == 4:
            if args[3] == "FULL":
                full_log_switch = True
            else:
                print(
                    '''Invalid argument! Please follow "IME_Interpreter_UI 4.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')
                sys.exit(
                    '''Invalid argument! Please follow "IME_Interpreter_UI 4.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL(optional)''')

        from imeinterpreter import *

        a = ImeInterpreter(path_to_ime_log_folder)
        with open(path_to_output_file, 'w') as outfile:
            # Write some text to the file
            outfile.write(a.generate_ime_interpreter_log_output(full_log_switch))
        print("Log output successful!")
        sys.exit("Log output successful!")
    else:
        root = Root()
        root.mainloop()
