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

from imeinterpreter import *
from tkinterui import *

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    #test_log_folder = "C:\\Users\\kufang\\OneDrive - Microsoft\\Projects\\IME project\\IMEintepreter Pycharm\\src\\test cases"
    #test_log_folder = "C:\\Users\\kufang\\Downloads\\Logs (4)\\Logs"
    #a = ImeInterpreter(test_log_folder)
    #print(a.generate_ime_interpreter_log_output(False))
    root = Root()
    root.mainloop()

