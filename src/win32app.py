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
    0. Not targeted to any group, could be Dependent app
    1. user group
    2. device group

    Intent:
    0. Not targeted, could be Dependent app
    1. Available
    3. Required
    4. Uninstall

    to differentiate dependent app and assignment filtered app:
    "AppApplicabilityStateDueToAssginmentFilters":1010
    "AppApplicabilityStateDueToAssginmentFilters":0
    If 1010:
    filtered and not applicable
    elif 0:
    filtered and applicable
    elif null: dependent app


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
        Whether this app has enforcement logs, like download + install
        Enforcement can be skipped due to:
        1. Win32 GRS
        2. Intent Install and detected
        3. Intent Uninstall and not detected
        """
        self.has_enforcement = False
        self.no_enforcement_reason = ""
        self.reason_need_output = False
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
        self.cur_app_log_enforcement_start_index = 99999
        self.cur_app_log_end_index = -99999
        self.is_root_app = False
        if len(subgraph_log) < 2:
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
        self.skip_installation = False
        self.applicability = False
        self.applicability_time = ""
        self.filter_state = None
        self.extended_applicability = True
        self.extended_applicability_time = ""
        self.proxy_url = ""
        self.download_do_mode = ""  # Foreground 12 hours, Background 10 minutes
        self.download_start_time = ""
        self.download_finish_time = ""
        self.download_file_size = -1
        self.size_need_to_download = -1
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

        self.uwp_detected_version = ""
        self.uwp_installed_version = ""
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
        self.supersedence_apps_list = {}
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

        self.enforcement_dict = {1000: 'SUCCEEDED', 2000: 'IN_PROGRESS', 2001: 'IN_PROGRESS_WAITING_CONTENT',
                                 2002: 'IN_PROGRESS_INSTALLING', 2003: 'IN_PROGRESS_WAITING_REBOOT',
                                 2004: 'IN_PROGRESS_WAITING_MAINTENANCE_WINDOW', 2005: 'IN_PROGRESS_WAITING_SCHEDULE',
                                 2006: 'IN_PROGRESS_DOWNLOADING_DEPENDENT_CONTENT',
                                 2007: 'IN_PROGRESS_INSTALLING_DEPENDENCIES', 2008: 'IN_PROGRESS_PENDING_REBOOT',
                                 2009: 'IN_PROGRESS_CONTENT_DOWNLOADED', 2013: 'IN_PROGRESS_WAITING_USERLOGON',
                                 4000: 'UNKNOWN', 5000: 'ERROR', 5001: 'ERROR_EVALUATING', 5002: 'ERROR_INSTALLING',
                                 5003: 'ERROR_RETRIEVING_CONTENT', 5004: 'ERROR_INSTALLING_DEPENDENCY',
                                 5005: 'ERROR_RETRIEVING_CONTENT_DEPENDENCY', 5006: 'ERROR_RULES_CONFLICT',
                                 5007: 'ERROR_WAITING_RETRY', 5008: 'ERROR_UNINSTALLING_SUPERSEDENCE',
                                 5009: 'ERROR_DOWNLOADING_SUPERSEDED', 5010: 'ERROR_UPDATING_VE',
                                 5011: 'ERROR_INSTALLING_LICENSE', 5012: 'ERROR_RETRIEVING_ALLOW_ALL_TRUSTED_APPS',
                                 5013: 'ERROR_NO_LICENSES_AVAILABLE', 5014: 'ERROR_OS_NOT_SUPPORTED'}

        # {v: k for k, v in enforcement_dict_reverse.items()}
        self.last_enforcement_state = "No enforcement state found"
        self.current_enforcement_status_report = None
        self.cur_enforcement_state = self.last_enforcement_state

        self.load_last_enforcement_state()
        self.initialize_app_log()
        self.interpret_app_log()
        # loaded after interpreting app log
        self.load_current_enforcement_state()
        self.determine_no_enforcement_reason()

    def determine_no_enforcement_reason(self):
        if not self.grs_expiry:
            self.no_enforcement_reason = "Win32 app GRS is not expired."
        elif self.pre_install_detection and self.intent != 4:
            self.no_enforcement_reason = "Intent is install and app is detected."
        elif not self.pre_install_detection and self.intent == 4:
            self.no_enforcement_reason = "Intent is uninstall and app is not detected."
        elif self.subgraph_is_standalone:
            self.no_enforcement_reason = self.cur_enforcement_state
            self.reason_need_output = True
        elif not self.subgraph_is_standalone:
            if self.cur_enforcement_state == "IN_PROGRESS_PENDING_REBOOT":
                self.no_enforcement_reason = "App pending reboot."
            else:
                self.no_enforcement_reason = "Subgraph may be missing required intent in dependency chain."
            self.reason_need_output = True
        else:
            self.no_enforcement_reason = self.cur_enforcement_state
            self.reason_need_output = True

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
        self.supersedence_apps_list = cur_app_dict['FlatDependencies']
        """
        "Action":110 : Auto uninstall: yes
        "Action":100: Auto uninstall: no
        [{"Action":110,"AppId":"d57bd65f-b00e-4814-a03f-3e8e8d2b3aa4","ChildId":"a1444e9f-a771-479e-a356-cadcade53b57","Type":1,"Level":0}]
        """
        self.install_command = cur_app_dict['InstallCommandLine']
        self.uninstall_command = cur_app_dict['UninstallCommandLine']
        self.intent = cur_app_dict["Intent"]
        self.target_type = cur_app_dict["TargetType"]
        if cur_app_dict["InstallerData"] is not None:
            self.app_type = "MSFB"
            self.package_identifier = json.loads(cur_app_dict["InstallerData"])["PackageIdentifier"]
        else:
            self.app_type = "Win32"

        self.install_context = self.last_enforcement_json[
            "InstallContext"] if self.last_enforcement_json is not None else -1
        # print(cur_app_dict)
        # print(cur_app_dict["InstallContext"])
        install_ex_as_json = json.loads(cur_app_dict['InstallEx'])
        self.device_restart_behavior = install_ex_as_json['DeviceRestartBehavior']

        """
            "AppApplicabilityStateDueToAssginmentFilters":1010
            "AppApplicabilityStateDueToAssginmentFilters":0
            If 1010:
            filtered and not applicable
            elif 0:
            filtered and applicable
            elif null: dependent app 
        """
        self.filter_state = cur_app_dict['AppApplicabilityStateDueToAssginmentFilters']

    def process_app_common_log(self):
        """
        All common processing log.
        Including
            predetection
            applicability
            current_enforcement_status_report

        :return: None
        """
        post_install = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith(LOG_WIN32_APP_PROCESSING_INDICATOR):
                cur_app_id = find_app_id_with_starting_string(cur_line, LOG_WIN32_APP_PROCESSING_INDICATOR)
                if cur_app_id != self.app_id:
                    continue
                elif 'effective intent: ' in cur_line or 'targeted intent: ' in cur_line:
                    """
                        Win32 Standalone + UWP flow
                        <![LOG[[Win32App][ActionProcessor] App with id: 9c393ca7-92fc-4e9e-94d0-f8e303734f7b, targeted intent: RequiredUninstall, and enforceability: Enforceable has projected enforcement classification: Ignore with desired state: NotPresent. Current state is: | Detection = Detected | Applicability =  Applicable | Reboot = Clean | Local start time = 1/1/0001 12:00:00 AM | Local deadline time = 1/1/0001 12:00:00 AM | GRS expired = False]LOG]!><time="15:40:04.5799146" date="3-25-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">

                        Win32 Dependency flow
                        <![LOG[[Win32App][ActionProcessor] App with id: 3dde4e19-3a18-4dec-b60e-720b919e1790, effective intent: RequiredInstall, and enforceability: Enforceable has projected enforcement classification: EnforcementPoint with desired state: Present. Current state is: | Detection = NotDetected | Applicability =  Applicable | Reboot = Clean | Local start time = 1/1/0001 12:00:00 AM | Local deadline time = 1/1/0001 12:00:00 AM | GRS expired = True]LOG]!><time="12:37:58.2967761" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">        
                    """
                    if not post_install:
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
            elif cur_line.startswith(LOG_WIN32_REPORTING_STATE_INDICATOR):
                cur_enforcement_index_start = cur_line.find('{"ApplicationId"')
                cur_enforcement_index_end = cur_line.find(LOG_ENDING_STRING)
                cur_app_id = find_app_id_with_starting_string(cur_line,
                                                                   'company portal based on report: {"ApplicationId":"')
                if cur_app_id != self.app_id:
                    continue
                app_json = cur_line[cur_enforcement_index_start:cur_enforcement_index_end]
                try:
                    self.current_enforcement_status_report = json.loads(app_json)
                except ValueError:
                    print("Json invalid, dropping")
            elif cur_line.startswith(LOG_WIN32_DOWNLOADING_INDICATOR):
                """
                Win32 app and MSFB UWP downloading start indicator
                
                <![LOG[[StatusService] Downloading app (id = 0557caed-3f50-499f-a39d-5b1179f78922, name [IMETest]Remote Desktop Connection Manager) via DO,
                <![LOG[[StatusService] Downloading app (id = 199981d9-dec0-410c-b563-7cc6fc4c33a6, name [IMETest]Company Portal) via WinGet, bytes 0/100 for user 8679bddf-b85f-473c-bc47-2ed0457ec9fb]LOG]!><time="10:08:43.9616518" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="19" file="">
                """
                cur_app_id = find_app_id_with_starting_string(cur_line, 'app (id = ')
                if cur_app_id != self.app_id:
                    continue

                if self.download_start_time == "":  # only the first line is the start time.
                    self.download_start_time = cur_time
                else:
                    cur_downloaded_size_index_start = cur_line.find(', bytes ') + len(', bytes ')
                    cur_downloaded_size_index_end = cur_line.find(' for user ')
                    cur_downloaded_size_percent = cur_line[cur_downloaded_size_index_start:cur_downloaded_size_index_end]
                    if '/' not in cur_downloaded_size_percent:
                        continue
                    downloaded_size_list = cur_downloaded_size_percent.split('/')
                    cur_downloaded_size, cur_needed_size = downloaded_size_list[0], downloaded_size_list[1]
                    self.download_file_size = int(cur_downloaded_size)
                    if int(cur_needed_size) > 0:
                        self.size_need_to_download = int(cur_needed_size)
                    continue

            elif cur_line.startswith(LOG_WIN32_EXECUTING_1_INDICATOR) or \
                    cur_line.startswith(LOG_UWP_EXECUTING_INDICATOR):
                post_install = True

    def interpret_app_log(self):
        self.process_app_common_log()

        if self.app_type == "MSFB":
            self.process_msfb_app_log()
        elif self.app_type == "Win32":
            if self.subgraph_is_standalone:
                self.process_win32_standalone_app_log()
            else:
                self.process_win32_dependency_app_log()

    def process_uwp_user_context_app_log(self):
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith(LOG_UWP_PROCMON_EXECUTING_INDICATOR):
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
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith('<![LOG[[Package Manager] BytesRequired - '):
                size_need_to_download_index_start = len('<![LOG[[Package Manager] BytesRequired - ')
                size_need_to_download_index_end = cur_line.find('BytesDownloaded - ')
                self.size_need_to_download = int(cur_line[size_need_to_download_index_start:size_need_to_download_index_end])
                size_downloaded_index_start = size_need_to_download_index_end + len('BytesDownloaded - ')
                size_downloaded_index_end = cur_line.find('DownloadProgress - ')

                download_progress_index_start = size_downloaded_index_end + len('DownloadProgress - ')
                download_progress_index_end = cur_line.find('InstallationProgress - ')
                """
                Download file size is only accurate at the first time of download progress reaches 1.
            
                <![LOG[[Package Manager] BytesRequired - 177447816BytesDownloaded - 175350664DownloadProgress - 0.988181584607387InstallationProgress - 0]LOG]!><time="08:22:29.1900138" date="3-3-2023" component="IntuneManagementExtension" context="" type="1" thread="161" file="">
	            <![LOG[[Package Manager] BytesRequired - 177447816BytesDownloaded - 177447816DownloadProgress - 1InstallationProgress - 0]LOG]!><time="08:22:29.4191464" date="3-3-2023" component="IntuneManagementExtension" context="" type="1" thread="161" file="">
	            <![LOG[[Package Manager] BytesRequired - 0BytesDownloaded - 0DownloadProgress - 1InstallationProgress - 0]LOG]
                """
                if cur_line[download_progress_index_start:download_progress_index_end] == '1' and int(cur_line[size_downloaded_index_start:size_downloaded_index_end]) > 0:
                    self.download_file_size = int(cur_line[size_downloaded_index_start:size_downloaded_index_end])

        if self.install_start_time != "" and self.download_finish_time != "":
            self.download_average_speed = self.convert_speedraw_to_string()

    def process_msfb_app_log(self):
        if not self.grs_expiry:
            return None
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
            if self.pre_install_detection:
                self.has_enforcement = True

        post_install = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)
            if cur_line.startswith(LOG_UWP_FINISH_EXECUTING_INDICATOR):
                """
                MSFB UWP install stop indicator
                <![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Completed execution for app with id:
                """
                cur_app_id = find_app_id_with_starting_string(cur_line, 'for app with id: ')
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

                post_install = True
                if self.install_finish_time == "":
                    self.install_finish_time = cur_time
                else:
                    continue
            elif cur_line.startswith(LOG_UWP_FINISH_DETECTION_INDICATOR):
                """
                MSFB UWP post-install detection result, with app version
                <![LOG[[Win32App][WinGetApp][WinGetAppDetectionExecutor] Completed detection for app with id: 
                """
                cur_app_id = find_app_id_with_starting_string(cur_line, 'Completed detection for app with id: ')
                if cur_app_id != self.app_id:
                    continue
                if post_install:
                    installed_version_index_start = cur_line.find('Installed version =  ') + len('Installed version =  ')
                    installed_version_index_end = cur_line.find(' | Reboot required ')
                    self.uwp_installed_version = cur_line[installed_version_index_start:installed_version_index_end]
                else:
                    detected_version_index_start = cur_line.find('Detected version: ') + len('Detected version: ')
                    detected_version_index_end = cur_line.find(' | Error code: ]')
                    self.uwp_detected_version = cur_line[detected_version_index_start:detected_version_index_end]

            elif cur_line.startswith('<![LOG[Processing state transition - Current State'):
                self.has_enforcement = True
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

        if self.install_context == 1:
            self.process_uwp_user_context_app_log()
        elif self.install_context == 2:
            self.process_uwp_system_context_app_log()

    def process_win32_standalone_app_log(self):
        if not self.grs_expiry:
            # skipped processing enforcement log due to GRS
            return None
        post_install = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)

            if cur_line.startswith('<![LOG[[Win32App][ActionProcessor] Evaluating '):
                # Evaluating whether app has enforcement
                cur_app_id = find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue
            elif cur_line.startswith('<![LOG[[Win32App][ActionProcessor] No action required for app with id:'):
                cur_app_id = find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue
                # Stop without enforcement
                self.has_enforcement = False
                self.cur_app_log_end_index = cur_line_index
                break
            elif cur_line.startswith('<![LOG[[Win32App] Downloading app on session'):
                """
                Win32 downloading start indicator
                
                <![LOG[[Win32App] Downloading app on session 2. App: 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]!><time="12:37:58.5140236" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                cur_app_id = find_app_id_with_starting_string(cur_line, '. App: ')
                if cur_app_id != self.app_id:
                    continue
                if self.download_start_time == "":
                    self.download_start_time = cur_time
                self.has_enforcement = True
            elif cur_line.startswith('<![LOG[[SendWebRequestInternal] Sending network request...  Current proxy is '):
                proxy_start_index = len('<![LOG[[SendWebRequestInternal] Sending network request...  Current proxy is ')
                proxy_end_index = cur_line.find(']LOG]!><')
                self.proxy_url = cur_line[proxy_start_index:proxy_end_index]
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
            elif cur_line.startswith('<![LOG[[Win32App DO] DO downloading is not finished within timeout'):
                if self.download_finish_time == "":
                    self.download_finish_time = cur_time
                    if self.download_average_speed == "":
                        self.download_average_speed = self.convert_speedraw_to_string()
                    self.download_success = False
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
                self.download_file_size = int(
                        (cur_line[file_size_index_start:file_size_index_end]).replace(',', ''))

                self.download_average_speed = self.convert_speedraw_to_string()
            elif cur_line.startswith('<![LOG[Cleaning up staging content'):
                if self.unzipping_success_time == "":
                    self.unzipping_success_time = cur_time
                    self.unzipping_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith('<![LOG[[Win32App] ===Step=== Execute retry '):
                if self.current_attempt_num == "0":
                    self.current_attempt_num = cur_line[42:43] + '1'
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
                    post_install = True
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

    def convert_speedraw_to_string(self):
        download_finish_time = datetime.datetime.strptime(self.download_finish_time[:-4],
                                                          '%m-%d-%Y %H:%M:%S')
        download_start_time = datetime.datetime.strptime(self.download_start_time[:-4], '%m-%d-%Y %H:%M:%S')
        download_average_speed_raw = self.download_file_size * 1.0 / (
                download_finish_time - download_start_time).total_seconds()

        if download_average_speed_raw > 1000000:
            download_average_speed_converted = str(
                round(download_average_speed_raw / 1000000, 1)) + " MB/s"
        elif download_average_speed_raw > 1000:
            download_average_speed_converted = str(
                round(download_average_speed_raw / 1000, 1)) + " KB/s"
        else:
            download_average_speed_converted = str(round(download_average_speed_raw, 1)) + " B/s"
        return download_average_speed_converted

    def process_win32_dependency_app_log(self):
        if not self.grs_expiry:
            # skipped processing enforcement log due to GRS
            return None
        post_install = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = get_timestamp_by_line(cur_line)

            if cur_line.startswith('<![LOG[[Win32App][ActionProcessor] Evaluating '):
                # Evaluating whether app has enforcement
                cur_app_id = find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue

            elif cur_line.startswith('<![LOG[[Win32App][ActionProcessor] No action required for app with id:'):
                cur_app_id = find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue
                # Stop without enforcement
                self.cur_app_log_end_index = cur_line_index
                break
            elif cur_line.startswith('<![LOG[[Win32App] Downloading app on session'):
                """
                Win32 downloading start indicator

                <![LOG[[Win32App] Downloading app on session 2. App: 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]!><time="12:37:58.5140236" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                cur_app_id = find_app_id_with_starting_string(cur_line, '. App: ')
                if cur_app_id != self.app_id:
                    continue

                self.cur_app_log_enforcement_start_index = cur_line_index

                if self.download_start_time == "":
                    self.download_start_time = cur_time
                self.has_enforcement = True
            elif cur_line.startswith('<![LOG[[SendWebRequestInternal] Sending network request...  Current proxy is '):
                proxy_start_index = len('<![LOG[[SendWebRequestInternal] Sending network request...  Current proxy is ')
                proxy_end_index = cur_line.find(']LOG]!><')
                self.proxy_url = cur_line[proxy_start_index:proxy_end_index]
            elif cur_line_index < self.cur_app_log_enforcement_start_index:
                continue
            elif 0 < self.cur_app_log_end_index < cur_line_index:
                break
            elif cur_line.startswith(
                        '<![LOG[[Win32App][DetectionActionHandler] Detection for policy with id: '):
                cur_app_id = find_app_id_with_starting_string(cur_line, 'policy with id: ')
                if cur_app_id != self.app_id:
                    continue
                if cur_line_index < self.cur_app_log_enforcement_start_index:
                    continue
                else:
                    if self.cur_app_log_end_index < self.cur_app_log_enforcement_start_index and post_install:
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

                if self.download_average_speed == "":
                    self.download_average_speed = self.convert_speedraw_to_string()
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith('<![LOG[Cleaning up staging content'):
                if self.unzipping_success_time == "":
                    self.unzipping_success_time = cur_time
                    self.unzipping_success = True
                else:
                    continue  # Means this is the line for other dependent apps\
            elif cur_line.startswith('<![LOG[[Win32App][ActionProcessor] Encountered unexpected state for app with id: '):
                """
                There is pre-install detection after download happens.
                Sometimes dependent app installation will also make the root app detected. But it will not know that until
                the root app is downloaded and ready to install.
                In this case, it will abort execution and mark as succeeded.
                
                <![LOG[[Win32App][ActionProcessor] Encountered unexpected state for app with id: 7e8adb8b-2ddc-45c0-90af-018a565aed0e. Expected the detection state to be "NotDetected" but found "Detected". Aborting processing for the current subgraph.]LOG]!><time="13:01:00.6450399" date="2-27-2023" component="IntuneManagementExtension" context="" type="1" thread="14" file="">

                
                """
                cur_app_id = find_app_id_with_starting_string(cur_line, '<![LOG[[Win32App][ActionProcessor] Encountered unexpected state for app with id: ')
                if cur_app_id != self.app_id:
                    continue
                self.skip_installation = True
            elif cur_line.startswith('<![LOG[[Win32App] ===Step=== Execute retry '):
                if self.current_attempt_num == "0":
                    self.current_attempt_num = cur_line[42:43] + '1'
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
                    post_install = True

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

    def generate_standalone_win32_app_meta_log_output(self, depth=0):
        """
        Include Win32 and UWP meta
        :return:
        """
        interpreted_log_output = ""

        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:', self.app_id), depth)
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:', self.app_name), depth)
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:', self.app_type), depth)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Not Assigned'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        left_string = 'App Intent:'
        right_string = ""
        if self.intent == 0:
            if self.subgraph_is_standalone:
                right_string = "Filtered by Assignment filter"
            else:
                right_string = "Dependent app"
        elif self.intent == 1:
            right_string = "Available Install"
        elif self.intent == 3:
            right_string = "Required Install"
        elif self.intent == 4:
            right_string = "Required Uninstall"

        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        if self.app_type == "MSFB":
            left_string = 'Detected Version'
            if self.uwp_detected_version != "":
                right_string = self.uwp_detected_version
            else:
                right_string = "None"
            interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                           right_string), depth)

            left_string = 'Installed Version'
            if self.uwp_installed_version != "":
                right_string = self.uwp_installed_version
            else:
                right_string = "None"
            interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                           right_string), depth)

        left_string = 'Has Dependent Apps:'
        right_string = 'No'
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, right_string), depth)

        # if not self.grs_expiry:
        #     log_line += 'Win32 app GRS is not expired. Win32 app will be reevaluated after last GRS time + 24 hours\n'

        return interpreted_log_output

    def generate_dependency_win32_app_meta_log_output(self, depth=0):
        interpreted_log_output = ""

        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:',
                                                                                                       self.app_id), depth)
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:',
                                                                                                       self.app_name), depth)
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:',
                                                                                                       self.app_type), depth)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Dependent App'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)

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

        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)

        left_string = 'Has Dependent Apps:'
        right_string = 'Yes'
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)
        # List Dependent apps

        for each_dependent_app_index in range(len(self.dependent_apps_list)):
            each_dependent_app = self.dependent_apps_list[each_dependent_app_index]
            child_app_id = each_dependent_app['ChildId']
            child_auto_install = each_dependent_app['Action']
            child_app_name = [match['Name'] for match in self.policy_json if match['Id'] == child_app_id].pop()
            right_string = str(each_dependent_app_index + 1) + ". " + child_app_id + " [Auto Install]: "

            if child_auto_install == 0:
                right_string += 'No '
            elif child_auto_install == 10:
                right_string += 'Yes '
            elif child_auto_install == 100:
                right_string += 'Supersedence ' #  not yet implemented.

            right_string += ('[' + child_app_name + ']')
            interpreted_log_output += \
                write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output\
                    ("", right_string, CONST_META_DEPENDENT_APP_VALUE_INDEX), depth)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += write_log_output_line_with_indent_depth(write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                       right_string), depth)

        return interpreted_log_output

    def compute_download_size_and_speed(self):
        computed_size_str = ""
        if self.download_file_size > 1000000000:
            computed_size_str = computed_size_str + 'Downloaded file size is: ' + str(
                    (self.download_file_size // 100000000) / 10.0) + ' GB'
        elif self.download_file_size > 1000000:
            computed_size_str = computed_size_str + 'Downloaded file size is: ' + str(
                    (self.download_file_size // 100000) / 10.0) + ' MB'
        elif self.download_file_size > 1000:
            computed_size_str = computed_size_str + 'Downloaded file size is: ' + str(
                    (self.download_file_size // 100) / 10.0) + ' KB'
        else:
            computed_size_str = computed_size_str + 'Downloaded file size is: ' + str(
                    self.download_file_size) + ' B'

        computed_speed_str = 'Average download speed is: ' + self.download_average_speed

        return computed_size_str, computed_speed_str

    def generate_msfb_uwp_post_download_log_output(self, depth=0):
        # This works for MSFB UWP
        interpreted_log_output = ""
        if not self.has_enforcement:
            if self.reason_need_output:
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + " No action required for this app. " + self.no_enforcement_reason + '\n', depth)
            return interpreted_log_output

        if self.intent != 4:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.download_start_time + ' Start downloading app using WinGet.\n',)
        if self.download_success:
            if self.intent != 4:
                interpreted_log_output += write_log_output_line_with_indent_depth(self.download_finish_time + ' WinGet mode download completed.\n')
                computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.download_finish_time + ' ' + computed_size_str + '\n', depth)

                interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_speed_str + '\n', depth)
        else:
            if self.intent != 4:
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' WinGet mode download FAILED! \n')
                computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
                if self.download_finish_time and self.download_file_size > -1:
                    interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.download_finish_time + ' ' + computed_size_str + '\n', depth)

                    interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.download_finish_time + ' ' + computed_speed_str + '\n', depth)
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output

        if self.install_context == 1:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.download_finish_time + ' Install Context: User\n')
        elif self.install_context == 2:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.download_finish_time + ' Install Context: System\n')
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.download_finish_time + ' Install Context: Unknown!\n')
        if self.installer_created_success:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_start_time + ' Installer process created successfully. Installer time out is 60 minutes.\n')
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Error creating installer process!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            if self.intent == 4:
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installer_exit_success:
            if self.intent == 4:
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.install_finish_time + ' Uninstallation is done.\n')
            else:
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.install_finish_time + ' Installation is done.\n')
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Installer process timeout!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            if self.install_error_message != "":
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Install Error message: ' + self.install_error_message + '\n')
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installation_result == "":
            self.installation_result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
        if self.intent == 4:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Uninstallation Result: ' + self.installation_result + '\n')
        else:
            # print(self.installation_result)
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Installation Result: ' + self.installation_result + '\n')

        if self.install_error_message != "":
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Install Error message: ' + self.install_error_message + '\n')

        if self.post_install_detection:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.post_install_detection_time +
                                       ' Detect app after processing: App is detected.\n'
                                       if self.post_install_detection_time != ""
                                       else self.install_finish_time +
                                            ' Detect app after processing: App is detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Uninstallation Result: ' + result + '\n')
                return interpreted_log_output
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n')
        else:
            if self.post_install_detection_time != "":
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.post_install_detection_time + ' Detect app after processing: App is NOT detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Fail"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output
        return interpreted_log_output

    def generate_win32app_post_download_log_output(self, depth=0):
        # This works for Win32, not MSFB UWP
        interpreted_log_output = ""

        """
        Handled in pre-download log output
        """
        if self.filter_state == 1010:
            return interpreted_log_output

        if not self.has_enforcement:
            if self.reason_need_output:
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + " No action required for this app. " + self.no_enforcement_reason + '\n', depth)
            return interpreted_log_output

        interpreted_log_output += write_log_output_line_with_indent_depth(self.download_start_time + ' Start downloading app using DO.\n', depth)
        if self.download_do_mode != "":
            interpreted_log_output += write_log_output_line_with_indent_depth(
                self.download_start_time + ' DO Download priority is: ' + self.download_do_mode + '\n', depth)
        if self.proxy_url != "":
            interpreted_log_output += write_log_output_line_with_indent_depth(
                self.download_start_time + ' Current Proxy is: ' + self.proxy_url + '\n', depth)
        if self.download_success:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.download_finish_time + ' DO mode download completed.\n', depth)
            computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
            interpreted_log_output += write_log_output_line_with_indent_depth(
                self.download_finish_time + ' ' + computed_size_str + '\n', depth)

            interpreted_log_output += write_log_output_line_with_indent_depth(
                self.download_finish_time + ' ' + computed_speed_str + '\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' DO mode download FAILED! \n', depth)
            if self.download_finish_time and self.download_file_size > -1:
                computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
                interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_size_str + '\n', depth)

                interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_speed_str + '\n', depth)

            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.hash_validate_success:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.hash_validate_success_time + ' Hash validation pass.\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Hash validation FAILED! \n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.decryption_success:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.decryption_success_time + ' Decryption success.\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Decryption FAILED!\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.unzipping_success:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.decryption_success_time + ' Unzipping success.\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Unzipping FAILED!\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.skip_installation:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.decryption_success_time + ' Aborting installation as app is detected.\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.install_context == 1:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_start_time + ' Install Context: User\n', depth)
        elif self.install_context == 2:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_start_time + ' Install Context: System\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_start_time + ' Install Context: Unknown!\n', depth)
        if self.intent == 4:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_start_time + ' Uninstall Command: ' + self.uninstall_command + '\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_start_time + ' Install Command: ' + self.install_command + '\n', depth)
        if self.installer_created_success:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_start_time + ' Installer process created successfully. Installer time out is 60 minutes.\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Error creating installer process!\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.installer_exit_success:
            if self.intent == 4:
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.install_finish_time + ' Uninstallation is done. Exit code is: ' + str(
                    self.install_exit_code) + '\n', depth)
            else:
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.install_finish_time + ' Installation is done. Exit code is: ' + str(
                    self.install_exit_code) + '\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' Installer process timeout!\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.intent == 4:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Uninstallation Result: ' + self.installation_result + '\n', depth)
        else:
            # print(self.installation_result)
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Installation Result: ' + self.installation_result + '\n', depth)

        '''
        RestartBehavior
        0: Return codes
        1: App install may force a device restart
        2: No specific action
        3: Intune will force a mandatory device restart
        '''
        if self.device_restart_behavior == 0:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Reboot Behavior: [Restart determined by return codes]\n', depth)
        elif self.device_restart_behavior == 1:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Reboot Behavior: [App install may force a device restart]\n', depth)
        elif self.device_restart_behavior == 2:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_finish_time + ' Reboot Status: [No specific action]\n', depth)
        elif self.device_restart_behavior == 3:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Reboot Behavior: [Intune will force a mandatory device restart]\n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.install_finish_time + ' Reboot Status: [Unknown]\n', depth)

        if self.post_install_detection:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                self.post_install_detection_time + ' Detect app after processing: App is detected.\n', depth) \
                if self.post_install_detection_time != "" \
                else write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Detect app after processing: App is detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Uninstallation Result: ' + result + '\n', depth)
                return interpreted_log_output
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
        else:
            if self.post_install_detection_time != "":
                interpreted_log_output += write_log_output_line_with_indent_depth(
                        self.post_install_detection_time + ' Detect app after processing: App is NOT detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Uninstallation Result: ' + result + '\n', depth)
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Fail"
                interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + ' App Installation Result: ' + result + '\n', depth)
                return interpreted_log_output

        return interpreted_log_output

    def generate_win32app_pre_download_log_output(self, depth=0):
        # including predetection, grs, applicability logging.
        # This works for Win32, MSFB UWP apps
        interpreted_log_output = ""

        """
        Filtered app does not have pre detection.
        """
        if self.filter_state == 1010:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.end_time + " App is not Applicable due to assignment filter.\n", depth)
            interpreted_log_output += write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: Not Applicable\n', depth)
            self.has_enforcement = False
            return interpreted_log_output

        if self.pre_install_detection:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + ' Detect app before processing: App is detected.\n', depth)
            if self.intent != 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += write_log_output_line_with_indent_depth(
                            self.pre_install_detection_time + ' App Installation Result: ' + result + '\n', depth)
                return interpreted_log_output
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + ' Detect app before processing: App is NOT detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "Success"
                interpreted_log_output += write_log_output_line_with_indent_depth(
                            self.pre_install_detection_time + ' App Uninstallation Result: ' + result + '\n', depth)
                return interpreted_log_output

        if not self.grs_expiry:
            # Output detection results only
            interpreted_log_output += write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + " Win32 app GRS is not expired. App will be detected only and NOT enforced.\n", depth)
            return interpreted_log_output

        if self.applicability:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.applicability_time + ' Applicability Check: Applicable \n', depth)
        else:
            interpreted_log_output += write_log_output_line_with_indent_depth(self.applicability_time + ' Applicability Check: NOT Applicable \n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "NOT Applicable"
            interpreted_log_output += write_log_output_line_with_indent_depth(self.applicability_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output

        return interpreted_log_output

    def generate_win32app_first_line_log_output(self, depth):
        interpreted_log_output = ""
        temp_log = ""
        temp_log += self.start_time + " Processing "
        if self.subgraph_is_standalone:
            temp_log += "Standalone app: ["
        else:
            if self.dependent_apps_list is not None:
                if self.is_root_app:
                    temp_log += "Root "
                else:
                    temp_log += "Dependent "
                temp_log += "app with Dependency: ["
            else:
                temp_log += "Dependent standalone app: ["
        temp_log += (self.app_name + "] " + 'with intent: ')

        "with intent "
        '''
        Intent:
        0. Dependent app
        1. Available
        3. Required
        4. Uninstall
        '''
        if self.intent == 0:
            temp_log += "Dependent app"
        elif self.intent == 1:
            temp_log += "Available Install"
        elif self.intent == 3:
            temp_log += "Required Install"
        elif self.intent == 4:
            temp_log += "Required Uninstall"
        temp_log += '\n'

        interpreted_log_output += write_log_output_line_with_indent_depth(temp_log, depth)
        return interpreted_log_output

    def generate_standalone_win32app_log_output(self, depth=0):
        interpreted_log_output = ""
        interpreted_log_output += self.generate_win32app_first_line_log_output(depth)
        interpreted_log_output += self.generate_win32app_pre_download_log_output(depth)

        if self.app_type == "Win32":
            interpreted_log_output += self.generate_win32app_post_download_log_output(depth)
        elif self.app_type == "MSFB":
            interpreted_log_output += self.generate_msfb_uwp_post_download_log_output()

        return interpreted_log_output

