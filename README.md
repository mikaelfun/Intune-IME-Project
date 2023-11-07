# Intune-IME-Project
IME tool to analyze IntuneManagementExtension.log

## Command line argument format:

Normal log output(igonoring non expired Subgraphs):

"IME Interpreter V4.0.exe" "path_to_ime_log_folder" "path_to_output_file"

Full log output:

"IME Interpreter V4.0.exe" "path_to_ime_log_folder" "path_to_output_file" FULL


## Tool screenshots:
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/826850da-7507-42d1-a576-05a58f6adb1f)
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/89a29853-390e-41b3-be97-7aee58e0dfba)
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/53940387-ff2f-47ac-bd5a-4004b5e37100)
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/3a608a15-8ff7-4bd1-87cc-ee982b7cc24d)
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/50c72966-7f3e-4221-96e0-a7e5d37cfcb7)
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/7c639896-bc13-4711-a857-4d69814b985a)
![image](https://github.com/mikaelfun/Intune-IME-Project/assets/31831389/16a290ec-f22b-457a-ad3b-adaa96ce16b3)






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

## Roadmap

1. PowerShell script diagnosis
2. Proactive remediation diagnosis
3. Win32 supersedence flow
