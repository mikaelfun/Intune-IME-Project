"""
This is Class def for Win32App.
Each SubGraph may contain multiple Win32Apps to process
Create this class object for each Win32Apps.

Error Code range: 5000 - 5999

Class hierarchy:
- ImeInterpreter
    - EMSLifeCycle
        - ApplicationPoller
            - SubGraph
                - Win32App

Note:
    TargetType:
    0. Dependent app
    1. user group
    2. device group

    Intent:
    0. Dependent app
    1. Available
    3. Required
    4. Uninstall

    TargetingMethod:
    0. Direct assignment
    1. Dependent app

    InstallContext:
    0. System Uninstall ?
    1. User context
    2. System context

    RestartBehavior:
"""
from logprocessinglibrary import *
import json
from constructinterpretedlog import *


class Win32App:
    def __init__(self, subgraph_log, app_id, app_name, policy_json, grs_time, subgraph_hash, grs_expiry=True,
                 subgraph_is_standalone=True, last_enforcement_json=None):
        self.app_name = app_name
        self.app_id = app_id
        self.app_type = 'Unknown'
        self.package_identifier = ""
        self.policy_json = policy_json
        self.grs_time = grs_time
        self.grs_expiry = grs_expiry
        self.subgraph_hash = subgraph_hash
        self.full_log = subgraph_log
        """
        Used to differentiate different Win32 apps logs in same subgraph in depdendency chain
        Each Win32 app own download+process+detect log part will be separeted by:
        
        Start: <![LOG[[Win32App] Downloading app on session
        End: <![LOG[[Win32App][ActionProcessor] Calculating desired states for all subgraphs
        
        Logic： 
        if start find, store index to cur_app_log_start_index
        If end find and index > cur_app_log_start_index, store index to cur_app_log_end_index
        If index > cur_app_log_end_index: skip processing rest logs.
        """
        self.cur_app_log_start_index = 99999
        self.cur_app_log_end_index = -99999
        self.is_root_app = False
        if len(subgraph_log) < 3:
            print("Error! Invalid Win32App log length. Exit 5001")
            return None
        self.subgraph_is_standalone = subgraph_is_standalone
        self.start_time = get_timestamp_by_line(self.full_log[0])
        self.end_time = get_timestamp_by_line(self.full_log[-1])
        # default to last line, in dependency flow, change to current app ending index line
        self.intent = -1
        '''
            0. Dependent app
            1. Available
            3. Required
            4. Uninstall
        '''
        self.effective_intent = ""
        self.target_type = -1
        '''
            0. Dependent app
            1. user group
            2. device group
        '''
        self.pre_install_detection = False
        self.pre_install_detection_time = ""
        self.post_install = False
        self.post_install_detection = False
        self.post_install_detection_time = ""
        self.applicability = False
        self.applicability_time = ""
        self.extended_applicability = True
        self.extended_applicability_time = ""
        self.download_do_mode = ""  # Foreground 12 hours, Background 10 minutes
        self.download_start_time = ""
        self.download_finish_time = ""
        self.download_file_size = -1
        self.download_average_speed = ""
        self.download_success = False
        self.hash_validate_success = False
        self.hash_validate_success_time = ""
        self.decryption_success = False
        self.decryption_success_time = ""
        self.unzipping_success = False
        self.unzipping_success_time = ""
        self.install_context = -1
        self.install_command = ""
        self.install_error_message = ""
        self.current_attempt_num = '0'  # 0, 1, 2    3 times in total
        self.install_start_time = ""
        self.installer_created_success = False
        self.uninstall_command = ""
        self.installer_thread_id = ''
        self.installation_result = ""
        self.install_finish_time = ""
        self.installer_exit_success = False
        self.install_exit_code = -10000
        '''
        RestartBehavior
        0: Return codes
        1: App install may force a device restart
        2: No specific action
        3: Intune will force a mandatory device restart
        '''
        self.device_restart_behavior = -1
        self.app_result = "FAIL"
        self.dependent_apps_list = {}
        """
        ReportingState: {"ApplicationId":"0557caed-3f50-499f-a39d-5b1179f78922","ResultantAppState":null,"ReportingImpact":null,"WriteableToStorage":true,"CanGenerateComplianceState":true,"CanGenerateEnforcementState":true,"IsAppReportable":true,"IsAppAggregatable":true,"AvailableAppEnforcementFlag":0,"DesiredState":2,"DetectionState":1,"DetectionErrorOccurred":false,"DetectionErrorCode":null,"ApplicabilityState":0,"ApplicabilityErrorOccurred":false,"ApplicabilityErrorCode":null,
        "EnforcementState":1000,
        
        "EnforcementErrorCode":0,"TargetingMethod":0,"TargetingType":1,"InstallContext":2,"Intent":3,"InternalVersion":1,"DetectedIdentityVersion":null,"RemovalReason":null}
        EnforcementState:
        'SUCCEEDED': 1000,
        'IN_PROGRESS': 2000,
        'IN_PROGRESS_WAITING_CONTENT': 2001,
        'IN_PROGRESS_INSTALLING': 2002,
        'IN_PROGRESS_WAITING_REBOOT': 2003,
        'IN_PROGRESS_WAITING_MAINTENANCE_WINDOW': 2004,
        'IN_PROGRESS_WAITING_SCHEDULE': 2005,
        'IN_PROGRESS_DOWNLOADING_DEPENDENT_CONTENT': 2006,
        'IN_PROGRESS_INSTALLING_DEPENDENCIES': 2007,
        'IN_PROGRESS_PENDING_REBOOT': 2008,
        'IN_PROGRESS_CONTENT_DOWNLOADED': 2009,
        'IN_PROGRESS_WAITING_USERLOGON': 2013,
        'UNKNOWN': 4000,
        'ERROR': 5000,
        'ERROR_EVALUATING': 5001,
        'ERROR_INSTALLING': 5002,
        'ERROR_RETRIEVING_CONTENT': 5003,
        'ERROR_INSTALLING_DEPENDENCY': 5004,
        'ERROR_RETRIEVING_CONTENT_DEPENDENCY': 5005,
        'ERROR_RULES_CONFLICT': 5006,
        'ERROR_WAITING_RETRY': 5007,
        'ERROR_UNINSTALLING_SUPERSEDENCE': 5008,
        'ERROR_DOWNLOADING_SUPERSEDED': 5009,
        'ERROR_UPDATING_VE': 5010,
        'ERROR_INSTALLING_LICENSE': 5011,
        'ERROR_RETRIEVING_ALLOW_ALL_TRUSTED_APPS': 5012,
        'ERROR_NO_LICENSES_AVAILABLE': 5013,
        'ERROR_OS_NOT_SUPPORTED': 5014
        """
        self.last_enforcement_json = last_enforcement_json
        enforcement_dict_reverse = {
            'SUCCEEDED': 1000,
            'IN_PROGRESS': 2000,
            'IN_PROGRESS_WAITING_CONTENT': 2001,
            'IN_PROGRESS_INSTALLING': 2002,
            'IN_PROGRESS_WAITING_REBOOT': 2003,
            'IN_PROGRESS_WAITING_MAINTENANCE_WINDOW': 2004,
            'IN_PROGRESS_WAITING_SCHEDULE': 2005,
            'IN_PROGRESS_DOWNLOADING_DEPENDENT_CONTENT': 2006,
            'IN_PROGRESS_INSTALLING_DEPENDENCIES': 2007,
            'IN_PROGRESS_PENDING_REBOOT': 2008,
            'IN_PROGRESS_CONTENT_DOWNLOADED': 2009,
            'IN_PROGRESS_WAITING_USERLOGON': 2013,
            'UNKNOWN': 4000,
            'ERROR': 5000,
            'ERROR_EVALUATING': 5001,
            'ERROR_INSTALLING': 5002,
            'ERROR_RETRIEVING_CONTENT': 5003,
            'ERROR_INSTALLING_DEPENDENCY': 5004,
            'ERROR_RETRIEVING_CONTENT_DEPENDENCY': 5005,
            'ERROR_RULES_CONFLICT': 5006,
            'ERROR_WAITING_RETRY': 5007,
            'ERROR_UNINSTALLING_SUPERSEDENCE': 5008,
            'ERROR_DOWNLOADING_SUPERSEDED': 5009,
            'ERROR_UPDATING_VE': 5010,
            'ERROR_INSTALLING_LICENSE': 5011,
            'ERROR_RETRIEVING_ALLOW_ALL_TRUSTED_APPS': 5012,
            'ERROR_NO_LICENSES_AVAILABLE': 5013,
            'ERROR_OS_NOT_SUPPORTED': 5014
        }
        self.enforcement_dict = {v: k for k, v in enforcement_dict_reverse.items()}
        # print(self.enforcement_dict)
        self.last_enforcement_state = "No enforcement state found"
        self.current_enforcement_status_report = None
        self.cur_enforcement_state = self.last_enforcement_state

        self.load_last_enforcement_state()
        self.initialize_app_log()
        self.interpret_app_log()
        # loaded after interpreting app log
        self.load_current_enforcement_state()

    def load_current_enforcement_state(self):
        if self.current_enforcement_status_report is not None and self.current_enforcement_status_report[
            'EnforcementState'] is not None and self.current_enforcement_status_report['EnforcementState'] \
                in self.enforcement_dict.keys():
            self.cur_enforcement_state = self.enforcement_dict[self.current_enforcement_status_report['EnforcementState']]
        else:
            self.cur_enforcement_state = self.last_enforcement_state

    def load_last_enforcement_state(self):
        self.last_enforcement_state = self.enforcement_dict[self.last_enforcement_json['EnforcementState']] if \
            self.last_enforcement_json is not None and self.last_enforcement_json['EnforcementState'] is not None \
            else "No enforcement state found"

    def initialize_app_log(self):
        cur_app_dict = None
        for each_dic in self.policy_json:
            if each_dic['Id'] == self.app_id:
                cur_app_dict = each_dic
                break
        if not cur_app_dict:
            print("Fatal! Win32App not found in get policy json!")
            return None
        self.dependent_apps_list = cur_app_dict['FlatDependencies']
        """
        "Action":0 : Auto install: no
        "Action":10: Auto install: yes
        [{'Action': 10, 'AppId': '471f61b1-58ad-431b-bd4d-386d3c953773', 'ChildId': 'b3d77df6-8802-414f-867e-457394d80cca', 'Type': 0, 'Level': 0}]
        # if self.dependent_apps_list:
        #    print(self.dependent_apps_list)
        """

        self.install_command = cur_app_dict['InstallCommandLine']
        self.uninstall_command = cur_app_dict['UninstallCommandLine']
        self.intent = cur_app_dict["Intent"]
        self.target_type = cur_app_dict["TargetType"]
        if cur_app_dict["InstallerData"] is not None:
            self.app_type = "UWP"
            self.package_identifier = json.loads(cur_app_dict["InstallerData"])["PackageIdentifier"]
        else:
            self.app_type = "Win32"

        self.install_context = self.last_enforcement_json[
            "InstallContext"] if self.last_enforcement_json is not None else 2
        # print(cur_app_dict)
        # print(cur_app_dict["InstallContext"])
        install_ex_as_json = json.loads(cur_app_dict['InstallEx'])
        self.device_restart_behavior = install_ex_as_json['DeviceRestartBehavior']

    def process_app_common_log(self):
        """
        All common processing log.
        Including
            predetection
            applicability
            current_enforcement_status_report

        :return: None
        """
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith('<![LOG[[Win32App][ActionProcessor] App with id: '):
                app_id_index_start = len('<![LOG[[Win32App][ActionProcessor] App with id: ')
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                if cur_app_id != self.app_id:
                    continue
                elif 'effective intent: ' in cur_line or 'targeted intent: ' in cur_line:
                    """
                        Win32 Standalone + UWP flow
                        <![LOG[[Win32App][ActionProcessor] App with id: 9c393ca7-92fc-4e9e-94d0-f8e303734f7b, targeted intent: RequiredUninstall, and enforceability: Enforceable has projected enforcement classification: Ignore with desired state: NotPresent. Current state is: | Detection = Detected | Applicability =  Applicable | Reboot = Clean | Local start time = 1/1/0001 12:00:00 AM | Local deadline time = 1/1/0001 12:00:00 AM | GRS expired = False]LOG]!><time="15:40:04.5799146" date="3-25-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">

                        Win32 Dependency flow
                        <![LOG[[Win32App][ActionProcessor] App with id: 3dde4e19-3a18-4dec-b60e-720b919e1790, effective intent: RequiredInstall, and enforceability: Enforceable has projected enforcement classification: EnforcementPoint with desired state: Present. Current state is: | Detection = NotDetected | Applicability =  Applicable | Reboot = Clean | Local start time = 1/1/0001 12:00:00 AM | Local deadline time = 1/1/0001 12:00:00 AM | GRS expired = True]LOG]!><time="12:37:58.2967761" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">        
                    """
                    if not self.post_install:
                        end_index = cur_line.find(', and enforceability')
                        self.effective_intent = cur_line[103:end_index]
                        detection_index_start = cur_line.find('Current state is: | Detection = ') + 32
                        detection_index_end = cur_line.find(' | Applicability = ')
                        if self.pre_install_detection_time == "":
                            self.pre_install_detection_time = cur_time
                            self.pre_install_detection = True if \
                                cur_line[detection_index_start:detection_index_end] == 'Detected' else False
                        applicability_index_start = detection_index_end + 20
                        applicability_index_end = cur_line.find(' | Reboot')
                        applicability_string = cur_line[applicability_index_start:applicability_index_end]
                        if applicability_string == 'Applicable':
                            self.applicability = True
                        else:
                            self.applicability = False
                        if self.applicability_time == "":
                            self.applicability_time = cur_time
                    else:
                        detection_index_start = cur_line.find('Current state is: | Detection = ') + 32
                        detection_index_end = cur_line.find(' | Applicability = ')
                        detection_string = cur_line[detection_index_start:detection_index_end]
                        self.post_install_detection = True if detection_string == 'Detected' else False
                        if self.post_install_detection_time == "":
                            self.post_install_detection_time = cur_time
            elif cur_line.startswith(
                    '<![LOG[[Win32App][ReportingManager] Sending status to company portal based on report: {"ApplicationId":"'):
                cur_enforcement_index_start = cur_line.find('{"ApplicationId"')
                cur_enforcement_index_end = cur_line.find(']LOG]!>')
                app_id_index_start = cur_enforcement_index_start + 18
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                if cur_app_id != self.app_id:
                    continue
                self.current_enforcement_status_report = json.loads(
                    cur_line[cur_enforcement_index_start:cur_enforcement_index_end])
            elif cur_line.startswith('<![LOG[[StatusService] Downloading app (id = '):
                """
                Win32 app and MSFB UWP downloading start indicator
                
                <![LOG[[StatusService] Downloading app (id = 0557caed-3f50-499f-a39d-5b1179f78922, name [IMETest]Remote Desktop Connection Manager) via DO,
                <![LOG[[StatusService] Downloading app (id = 199981d9-dec0-410c-b563-7cc6fc4c33a6, name [IMETest]Company Portal) via WinGet, bytes 0/100 for user 8679bddf-b85f-473c-bc47-2ed0457ec9fb]LOG]!><time="10:08:43.9616518" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="19" file="">
                """
                app_id_index_start = cur_line.find('app (id = ') + 10
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                if cur_app_id != self.app_id:
                    continue
                if self.download_start_time == "":  # only the first line is the start time.
                    self.download_start_time = cur_time
                else:
                    continue
            elif cur_line.startswith('<![LOG[[Win32App][ExecutionActionHandler] Handler '):
                self.post_install = True

    def interpret_app_log(self):
        self.process_app_common_log()

        if self.app_type == "UWP":
            self.process_uwp_app_log()
        elif self.app_type == "Win32":
            self.process_win32_app_log()

    def process_uwp_user_context_app_log(self):
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith('<![LOG[[ProcessMonitor] Calling CreateProcessAsUser:'):
                """
                MSFB UWP indicator for User Context
                <![LOG[[ProcessMonitor] Calling CreateProcessAsUser: '"C:\Program Files (x86)\Microsoft Intune Management Extension\agentexecutor.exe" -executeWinGet -operationType "Detection"
                <![LOG[[ProcessMonitor] Calling CreateProcessAsUser: '"C:\Program Files (x86)\Microsoft Intune Management Extension\agentexecutor.exe" -executeWinGet -operationType "ApplicabilityCheck"
                <![LOG[[ProcessMonitor] Calling CreateProcessAsUser: '"C:\Program Files (x86)\Microsoft Intune Management Extension\agentexecutor.exe" -executeWinGet -operationType "Install"
                <![LOG[[ProcessMonitor] Calling CreateProcessAsUser: '"C:\Program Files (x86)\Microsoft Intune Management Extension\agentexecutor.exe" -executeWinGet -operationType "Uninstall"
                """
                if '-operationType "Uninstall"' in cur_line:
                    """
                    Uninstall bypass app download
                    MSFB UWP install start indicator for User Context
                    """
                    self.installer_created_success = True
                    if self.install_start_time == "":
                        self.install_start_time = cur_time

                elif '-operationType "Install"' in cur_line:
                    """
                    MSFB UWP install start indicator for User Context
                    """
                    self.installer_created_success = True
                    if self.install_start_time == "":
                        self.install_start_time = cur_time

    def process_uwp_system_context_app_log(self):
        """
        System context will create new thread when installing the app.

        <![LOG[[Win32App][WinGetApp][AppPackageManager] No installed version found. Performing an app installation.]LOG]!><time="10:08:20.0111484" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
        <![LOG[[StatusService] No subscribers to DownloadProgressHandler.]LOG]!><time="10:08:20.0739368" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="19" file="">

        thread will continue at app execution results:
        <![LOG[[Win32App][WinGetApp][WinGetAppDetectionExecutor] Completed detection for app with id: 9c393ca7-92fc-4e9e-94d0-f8e303734f7b.

        :return:
        """
        pass

    def process_uwp_app_log(self):
        # UWP app don't need to hash validate, decrypt, unzip
        self.hash_validate_success = True
        self.decryption_success = True
        self.unzipping_success = True
        self.hash_validate_success_time = self.pre_install_detection_time
        self.decryption_success_time = self.pre_install_detection_time
        self.unzipping_success_time = self.pre_install_detection_time

        # Initialize cur_app_log_end_index to end of log as UWP app has 1 app per subgraph
        self.cur_app_log_end_index = len(self.full_log) - 1
        # UWP app don't need to download to uninstall
        if self.intent == 4:
            self.download_success = True
            if self.download_start_time == "":
                self.download_start_time = self.pre_install_detection_time
                self.download_finish_time = self.pre_install_detection_time
            else:
                self.download_finish_time = self.download_start_time

        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith(
                    '<![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Completed execution for app with id: '):
                """
                MSFB UWP install stop indicator
                <![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Completed execution for app with id:
                """
                app_id_index_start = cur_line.find('for app with id: ') + len('for app with id: ')
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                if cur_app_id != self.app_id:
                    continue

                self.installer_exit_success = True

                install_action_status_index_start = cur_line.find('Action status: ') + len('Action status: ')
                install_action_status_index_end = cur_line.find('Enforcement state') - len('Enforcement state') - 3
                self.installation_result = cur_line[install_action_status_index_start:install_action_status_index_end]

                install_message_status_index_start = cur_line.find('Installer Exception message = ') + len(
                    'Installer Exception message = ')
                install_message_status_index_end = cur_line.find('Execution result') - 3
                self.install_error_message = cur_line[
                                             install_message_status_index_start:install_message_status_index_end]

                self.post_install = True
                if self.install_finish_time == "":
                    self.install_finish_time = cur_time
                else:
                    continue
            elif cur_line.startswith('<![LOG[Processing state transition - Current State'):
                if 'Install In Progress With Event: Download Started' in cur_line:
                    """
                    MSFB UWP download start indicator
                    <![LOG[Processing state transition - Current State:Install In Progress With Event: Download Started]
                    """
                    self.download_start_time = cur_time
                elif 'Download In Progress With Event: Download Finished' in cur_line:
                    """
                    MSFB UWP download stop indicator
                    <![LOG[Processing state transition - Current State:Download In Progress With Event: Download Finished]
                    """
                    self.download_finish_time = cur_time
                    self.download_success = True
                elif 'Download Complete With Event: Continue Install' in cur_line:
                    """
                    MSFB UWP install start indicator
                    <![LOG[Processing state transition - Current State:Queued With Event: Install Started.]
                    """
                    self.install_start_time = cur_time
                    self.installer_created_success = True
                # elif 'Download In Progress With Event: Install Error' in cur_line:
                #     """
                #     MSFB UWP install stop indicator
                #     <![LOG[Processing state transition - Current State:Download In Progress With Event: Install Error]
                #     """
                #     self.install_finish_time = cur_time
                #     self.installer_exit_success = True

        if self.install_context == 1:
            self.process_uwp_user_context_app_log()
        elif self.install_context == 2:
            self.process_uwp_system_context_app_log()

    def process_win32_app_log(self):
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)

            if cur_line.startswith('<![LOG[[Win32App] Downloading app on session'):
                """
                Win32 downloading start indicator
                
                <![LOG[[Win32App] Downloading app on session 2. App: 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]!><time="12:37:58.5140236" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                app_id_index_start = cur_line.find('. App: ') + 7
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                if cur_app_id != self.app_id:
                    continue

                self.cur_app_log_start_index = cur_line_index

                if self.download_start_time == "":
                    self.download_start_time = cur_time
            else:
                if cur_line_index < self.cur_app_log_start_index:
                    continue  # wrong app id
                elif 0 < self.cur_app_log_end_index < cur_line_index:
                    break
                elif cur_line.startswith('<![LOG[[Win32App][ActionProcessor] Calculating desired states for all subgraphs.'):
                    # This applies to Dependency Chain only
                    if self.cur_app_log_end_index < self.cur_app_log_start_index:
                        self.cur_app_log_end_index = cur_line_index
                        self.end_time = cur_time
                elif cur_line.startswith('<![LOG[Waiting '):
                    if cur_line.startswith('<![LOG[Waiting 600000 ms for 1 jobs to complete'):
                        if self.download_do_mode == "":
                            self.download_do_mode = "BACKGROUND(10 min timeout)"
                        else:
                            continue  # Means this is the line for other dependent apps
                    elif cur_line.startswith('<![LOG[Waiting 43200000 ms for 1 jobs to complete]'):
                        if self.download_do_mode == "":
                            self.download_do_mode = "FOREGROUND(12 hour timeout)"
                        else:
                            continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[Notified DO Service the job is complete.'):
                    if self.download_finish_time == "":
                        self.download_finish_time = cur_time
                        self.download_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] file hash validation pass'):
                    if self.hash_validate_success_time == "":
                        self.hash_validate_success_time = cur_time
                        self.hash_validate_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] Decryption is done successfully.]'):
                    if self.decryption_success_time == "":
                        self.decryption_success_time = cur_time
                        self.decryption_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] Downloaded file size '):
                    file_size_index_start = 38
                    file_size_index_end = cur_line.find(']LOG]!') - 3
                    if self.download_file_size == -1:
                        self.download_file_size = int(
                            (cur_line[file_size_index_start:file_size_index_end]).replace(',', ''))
                    else:
                        continue  # Means this is the line for other dependent apps

                    download_finish_time = datetime.datetime.strptime(self.download_finish_time[:-4],
                                                                      '%m-%d-%Y %H:%M:%S')
                    download_start_time = datetime.datetime.strptime(self.download_start_time[:-4], '%m-%d-%Y %H:%M:%S')
                    download_average_speed_raw = self.download_file_size * 1.0 / (download_finish_time - download_start_time).total_seconds()
                    download_average_speed_converted = ""
                    if self.download_average_speed == "":
                        if download_average_speed_raw > 1000000:
                            download_average_speed_converted = str(round(download_average_speed_raw / 1000000, 1)) + " MB/s"
                        elif download_average_speed_raw > 1000:
                            download_average_speed_converted = str(round(download_average_speed_raw / 1000, 1)) + " KB/s"
                        else:
                            download_average_speed_converted = str(round(download_average_speed_raw, 1)) + " B/s"
                        self.download_average_speed = download_average_speed_converted
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[Cleaning up staging content'):
                    if self.unzipping_success_time == "":
                        self.unzipping_success_time = cur_time
                        self.unzipping_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] ===Step=== Execute retry '):
                    if self.current_attempt_num == "":
                        self.current_attempt_num = cur_line[42:43]
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] Create installer process successfully.]LOG]'):
                    if self.install_start_time == "":
                        self.install_start_time = cur_time
                        self.installer_created_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] process id = '):
                    installer_thread_id_index_start = cur_line.find('process id = ') + len('process id = ')
                    installer_thread_id_index_stop = cur_line.find(']LOG]!')
                    if self.installer_thread_id == "":
                        self.installer_thread_id = \
                            cur_line[installer_thread_id_index_start:installer_thread_id_index_stop]
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] Installation is done, collecting result]LOG]!'):
                    if self.install_finish_time == "":
                        self.install_finish_time = cur_time
                        self.post_install = True
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] lpExitCode '):

                    if cur_line.startswith('<![LOG[[Win32App] lpExitCode is defined as '):
                        installation_result_index_start = len('<![LOG[[Win32App] lpExitCode is defined as ')
                        installation_result_index_stop = cur_line.find(']LOG]!')
                        if self.installation_result == "":
                            self.installer_exit_success = True
                            self.installation_result = cur_line[
                                                   installation_result_index_start:installation_result_index_stop]
                        else:
                            continue  # Means this is the line for other dependent apps
                    else:
                        exit_code_index_start = len('<![LOG[[Win32App] lpExitCode')
                        exit_code_index_stop = cur_line.find(']LOG]!')
                        if self.install_exit_code == -10000:
                            self.installer_exit_success = True
                            self.install_exit_code = int(cur_line[exit_code_index_start:exit_code_index_stop])
                        else:
                            continue  # Means this is the line for other dependent apps
                elif cur_line.startswith('<![LOG[[Win32App] Admin did NOT set mapping for lpExitCode: '):
                    installation_result_index_start = len('<![LOG[[Win32App] ')
                    installation_result_index_stop = cur_line.find('of app: ')
                    if self.installation_result == "":
                        self.installer_exit_success = True
                        self.installation_result = \
                            cur_line[installation_result_index_start:installation_result_index_stop]
                    else:
                        continue  # Means this is the line for other dependent apps

    def generate_standalone_win32_app_meta_log_output(self):
        interpreted_log_output = ""

        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:', self.app_id)
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:', self.app_name)
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:', self.app_type)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Dependent App'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        left_string = 'App Intent:'
        right_string = ""
        if self.intent == 0:
            right_string = "Dependent app"
        elif self.intent == 1:
            right_string = "Available Install"
        elif self.intent == 3:
            right_string = "Required Install"
        elif self.intent == 4:
            right_string = "Required Uninstall"

        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        left_string = 'Has Dependent Apps:'
        right_string = 'No'
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string)

        # if not self.grs_expiry:
        #     log_line += 'Win32 app GRS is not expired. Win32 app will be reevaluated after last GRS time + 24 hours\n'

        return interpreted_log_output

    def generate_dependency_win32_app_meta_log_output(self):
        interpreted_log_output = ""

        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:',
                                                                                                       self.app_id)
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:',
                                                                                                       self.app_name)
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:',
                                                                                                       self.app_type)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Dependent App'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)

        left_string = 'App Intent:'
        right_string = ""
        if self.intent == 0:
            right_string = "Dependent app"
        elif self.intent == 1:
            right_string = "Available Install"
        elif self.intent == 3:
            right_string = "Required Install"
        elif self.intent == 4:
            right_string = "Required Uninstall"

        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)

        left_string = 'Has Dependent Apps:'
        right_string = 'Yes'
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)
        # List Dependent apps

        for each_dependent_app_index in range(len(self.dependent_apps_list)):
            each_dependent_app = self.dependent_apps_list[each_dependent_app_index]
            child_app_id = each_dependent_app['ChildId']
            child_auto_install = each_dependent_app['Action']
            child_app_name = [match['Name'] for match in self.policy_json if match['Id'] == child_app_id].pop()
            right_string = str(each_dependent_app_index + 1) + ". " + child_app_id + " [Auto Install]: "
            if child_auto_install == 10:
                right_string += 'Yes '
            elif child_auto_install == 0:
                right_string += 'No '
            right_string += ('[' + child_app_name + ']')
            interpreted_log_output += \
                write_two_string_at_left_and_middle_with_filled_spaces_to_log_output\
                    ("", right_string, CONST_META_DEPENDENT_APP_VALUE_INDEX)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string)

        return interpreted_log_output

    def generate_msfb_uwp_post_download_log_output(self):
        # This works for MSFB UWP
        interpreted_log_output = ""
        if self.intent != 4:
            interpreted_log_output += (self.download_start_time + ' Start downloading app using WinGet.\n')
        if self.download_success:
            if self.intent != 4:
                interpreted_log_output += (self.download_finish_time + ' WinGet mode download completed.\n')
            # interpreted_log_output += (
            #         self.download_finish_time + ' Average download speed is: ' + self.download_average_speed + '\n')
        else:
            if self.intent != 4:
                interpreted_log_output += (self.end_time + ' WinGet mode download FAILED! \n')
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output
        if self.install_context == 1:
            interpreted_log_output += (self.download_finish_time + ' Install Context: User\n')
        elif self.install_context == 2:
            interpreted_log_output += (self.download_finish_time + ' Install Context: System\n')
        else:
            interpreted_log_output += (self.download_finish_time + ' Install Context: Unknown!\n')
        if self.installer_created_success:
            interpreted_log_output += (
                    self.install_start_time + ' Installer process created successfully. Installer time out is 60 minutes.\n')
        else:
            interpreted_log_output += (self.end_time + ' Error creating installer process!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            if self.intent == 4:
                interpreted_log_output += (self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installer_exit_success:
            if self.intent == 4:
                interpreted_log_output += (
                        self.install_finish_time + ' Uninstallation is done.\n')
            else:
                interpreted_log_output += (
                        self.install_finish_time + ' Installation is done.\n')
        else:
            interpreted_log_output += (self.end_time + ' Installer process timeout!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            if self.install_error_message != "":
                interpreted_log_output += (self.end_time + ' Install Error message: ' + self.install_error_message + '\n')
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installation_result == "":
            self.installation_result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
        if self.intent == 4:
            interpreted_log_output += (
                    self.install_finish_time + ' Uninstallation Result: ' + self.installation_result + '\n')
        else:
            # print(self.installation_result)
            interpreted_log_output += (
                    self.install_finish_time + ' Installation Result: ' + self.installation_result + '\n')

        if self.install_error_message != "":
            interpreted_log_output += (self.end_time + ' Install Error message: ' + self.install_error_message + '\n')

        if self.post_install_detection:
            interpreted_log_output += (self.post_install_detection_time +
                                       ' Detect app after processing: App is detected.\n'
                                       if self.post_install_detection_time != ""
                                       else self.install_finish_time +
                                            ' Detect app after processing: App is detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += (self.end_time + ' App Uninstallation Result: ' + result + '\n')
                return interpreted_log_output
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
        else:
            if self.post_install_detection_time != "":
                interpreted_log_output += (
                        self.post_install_detection_time + ' Detect app after processing: App is NOT detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += (self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Fail"
                interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output
        return interpreted_log_output

    def generate_win32app_post_download_log_output(self):
        # This works for Win32, not MSFB UWP
        interpreted_log_output = ""

        interpreted_log_output += (self.download_start_time + ' Start downloading app using DO.\n')
        interpreted_log_output += (
                self.download_start_time + ' DO Download priority is: ' + self.download_do_mode + '\n')
        if self.download_success:
            interpreted_log_output += (self.download_finish_time + ' DO mode download completed.\n')
            if self.download_file_size > 1000000000:
                interpreted_log_output += (
                        self.download_finish_time + ' Downloaded file size is: ' + str(self.download_file_size // 1000000000) + ' GB\n')
            elif self.download_file_size > 1000000:
                interpreted_log_output += (
                        self.download_finish_time + ' Downloaded file size is: ' + str(self.download_file_size // 1000000) + ' MB\n')
            elif self.download_file_size > 1000:
                interpreted_log_output += (
                        self.download_finish_time + ' Downloaded file size is: ' + str(self.download_file_size // 1000) + ' KB\n')
            else:
                interpreted_log_output += (
                        self.download_finish_time + ' Downloaded file size is: ' + str(self.download_file_size) + ' B\n')

            interpreted_log_output += (
                    self.download_finish_time + ' Average download speed is: ' + self.download_average_speed + '\n')
        else:
            interpreted_log_output += (self.end_time + ' DO mode download FAILED! \n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.hash_validate_success:
            interpreted_log_output += (self.hash_validate_success_time + ' Hash validation pass.\n')
        else:
            interpreted_log_output += (self.end_time + ' Hash validation FAILED! \n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.decryption_success:
            interpreted_log_output += (self.decryption_success_time + ' Decryption success.\n')
        else:
            interpreted_log_output += (self.end_time + ' Decryption FAILED!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.unzipping_success:
            interpreted_log_output += (self.decryption_success_time + ' Unzipping success.\n')
        else:
            interpreted_log_output += (self.end_time + ' Unzipping FAILED!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.install_context == 1:
            interpreted_log_output += (self.install_start_time + ' Install Context: User\n')
        elif self.install_context == 2:
            interpreted_log_output += (self.install_start_time + ' Install Context: System\n')
        else:
            interpreted_log_output += (self.install_start_time + ' Install Context: Unknown!\n')
        if self.intent == 4:
            interpreted_log_output += (self.install_start_time + ' Uninstall Command: ' + self.uninstall_command + '\n')
        else:
            interpreted_log_output += (self.install_start_time + ' Install Command: ' + self.install_command + '\n')
        if self.installer_created_success:
            interpreted_log_output += (
                    self.install_start_time + ' Installer process created successfully. Installer time out is 60 minutes.\n')
        else:
            interpreted_log_output += (self.end_time + ' Error creating installer process!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installer_exit_success:
            if self.intent == 4:
                interpreted_log_output += (
                        self.install_finish_time + ' Uninstallation is done. Exit code is: ' + str(
                    self.install_exit_code) + '\n')
            else:
                interpreted_log_output += (
                        self.install_finish_time + ' Installation is done. Exit code is: ' + str(
                    self.install_exit_code) + '\n')
        else:
            interpreted_log_output += (self.end_time + ' Installer process timeout!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.intent == 4:
            interpreted_log_output += (
                    self.install_finish_time + ' Uninstallation Result: ' + self.installation_result + '\n')
        else:
            # print(self.installation_result)
            interpreted_log_output += (
                    self.install_finish_time + ' Installation Result: ' + self.installation_result + '\n')

        '''
        RestartBehavior
        0: Return codes
        1: App install may force a device restart
        2: No specific action
        3: Intune will force a mandatory device restart
        '''
        if self.device_restart_behavior == 0:
            interpreted_log_output += (
                    self.install_finish_time + ' Reboot Behavior: [Restart determined by return codes]\n')
        elif self.device_restart_behavior == 1:
            interpreted_log_output += (
                    self.install_finish_time + ' Reboot Behavior: [App install may force a device restart]\n')
        elif self.device_restart_behavior == 2:
            interpreted_log_output += (self.install_finish_time + ' Reboot Status: [No specific action]\n')
        elif self.device_restart_behavior == 3:
            interpreted_log_output += (
                    self.install_finish_time + ' Reboot Behavior: [Intune will force a mandatory device restart]\n')
        else:
            interpreted_log_output += (self.install_finish_time + ' Reboot Status: [Unknown]\n')

        if self.post_install_detection:
            interpreted_log_output += (self.post_install_detection_time +
                                       ' Detect app after processing: App is detected.\n'
                                       if self.post_install_detection_time != ""
                                       else self.install_finish_time +
                                            ' Detect app after processing: App is detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += (self.end_time + ' App Uninstallation Result: ' + result + '\n')
                return interpreted_log_output
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
        else:
            if self.post_install_detection_time != "":
                interpreted_log_output += (
                        self.post_install_detection_time + ' Detect app after processing: App is NOT detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += (self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Fail"
                interpreted_log_output += (self.end_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output

        return interpreted_log_output

    def generate_win32app_pre_download_log_output(self):
        # including predetection, grs, applicability logging.
        # This works for Win32, MSFB UWP apps
        interpreted_log_output = ""
        if self.pre_install_detection:
            interpreted_log_output += (
                    self.pre_install_detection_time + ' Detect app before processing: App is detected.\n')
            if self.intent != 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += (
                            self.pre_install_detection_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output, True
        else:
            interpreted_log_output += (
                    self.pre_install_detection_time + ' Detect app before processing: App is NOT detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += (
                            self.pre_install_detection_time + ' App Uninstallation Result: ' + result + '\n')
                return interpreted_log_output, True

        if not self.grs_expiry:
            # Output detection results only
            interpreted_log_output += (
                    self.pre_install_detection_time + " Win32 app GRS is not expired. App will be detected only and NOT enforced.\n")
            return interpreted_log_output, True

        if self.applicability:
            interpreted_log_output += (self.applicability_time + ' Applicability Check: Applicable \n')
        else:
            interpreted_log_output += (self.applicability_time + ' Applicability Check: NOT Applicable \n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "NOT Applicable"
            interpreted_log_output += (self.applicability_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output, True

        return interpreted_log_output, False

    def generate_win32app_first_line_log_output(self):
        interpreted_log_output = ""
        interpreted_log_output += (self.start_time + " Processing ")
        if self.subgraph_is_standalone:
            interpreted_log_output += "Standalone app: ["
        else:
            if self.dependent_apps_list is not None:
                if self.is_root_app:
                    interpreted_log_output += "Root "
                else:
                    interpreted_log_output += "Dependent "
                interpreted_log_output += "app with Dependency: ["
            else:
                interpreted_log_output += "Dependent standalone app: ["
        interpreted_log_output += (self.app_name + "] " + 'with intent: ')

        "with intent "
        '''
        Intent:
        0. Dependent app
        1. Available
        3. Required
        4. Uninstall
        '''
        if self.intent == 0:
            interpreted_log_output += "Dependent app"
        elif self.intent == 1:
            interpreted_log_output += "Available Install"
        elif self.intent == 3:
            interpreted_log_output += "Required Install"
        elif self.intent == 4:
            interpreted_log_output += "Required Uninstall"

        interpreted_log_output += '\n'
        return interpreted_log_output

    def generate_standalone_win32app_log_output(self):
        interpreted_log_output = ""
        interpreted_log_output += self.generate_win32app_first_line_log_output()
        temp_log, stop_processing_log = self.generate_win32app_pre_download_log_output()
        interpreted_log_output += temp_log
        if stop_processing_log:
            return interpreted_log_output
        else:
            if self.app_type == "Win32":
                interpreted_log_output += self.generate_win32app_post_download_log_output()
            elif self.app_type == "UWP":
                interpreted_log_output += self.generate_msfb_uwp_post_download_log_output()
        return interpreted_log_output

    def generate_dependency_win32app_log_output(self):
        interpreted_log_output = ""
        temp_log, processing_stop = self.generate_win32app_pre_download_log_output()
        interpreted_log_output += temp_log
        # bool_need_last_part_output = self.applicability and self.grs_expiry and ((self.pre_install_detection and self.intent == 4) or (not self.pre_install_detection and self.intent != 4))
        # if not processing_stop:
        #    interpreted_log_output += self.generate_win32app_post_download_log_output()
        return interpreted_log_output