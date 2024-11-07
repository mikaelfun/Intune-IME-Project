# Intune-IME-Project
IME tool to analyze IntuneManagementExtension.log, AgentExecutor.log and AppWorkload.log

# How to use:
Download and unzip IME Interpreter V5.0.zip from release.
There are 2 programs:
1. IME Interpreter V5.0.exe: Main program with debug window for general use.
2. update.exe: Updater program which is used to update *.py and *.json files from GitHub src folder. Whenever there is a hotpatch, run this program and it can be updated right away.

Please note that the program maybe caught and blocked by defender antivirus. If it does, go to the antivirus protection history and allow the blocked file. Both exe's are safe to use without any viruses. You can check update.py and programentry.py for security review.


## Command line argument format:

Normal log output(igonoring non expired Subgraphs):

"IME Interpreter V5.0.exe" "path_to_ime_log_folder" "path_to_output_file"

Full log output:

"IME Interpreter V5.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL


## Tool screenshots:
![readmeimage](https://github.com/user-attachments/assets/e5d7192e-b9c8-4ffe-8c2d-12de54591b3a)

![readmeimage1](https://github.com/user-attachments/assets/0ac360c3-56d1-4105-9306-d5e04ee55595)





## Currently supported scenarios:

1. App poller meta: EspPhase, user session, Comgt app workload status, required/available/selected apps mode, app number after filter
2. Required App processing flow
3. Available App processing flow
4. App Uninstallation flow
5. Not Applicable
6. Dependent App processing flow
7. DO download priority
8. GRS skip flow
9. Incomplete Application Poller/Win32 app processing flow
10. MSFB UWP app flow
11. PowerShell diagnosis
12. Proactive remediation diagnosis
13. Win32 supersedence flow

## Roadmap
1. Multi-user session scenario. Eg. when multiple aad users with Intune license is logged in to the same device, it will process apps for each user session. This scenario is currently not implemented.
