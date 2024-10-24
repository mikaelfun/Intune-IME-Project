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
import datetime
import json
import logprocessinglibrary
import constructinterpretedlog


class Win32App:
    def __init__(self, subgraph_log, app_id, app_name, policy_json, grs_time, subgraph_hash, grs_expiry=True,
                 subgraph_type=1, last_enforcement_json=None):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
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
        self.subgraph_type = subgraph_type
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[0])
        self.end_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[-1])
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
        self.post_download_detection = False
        self.post_download_detection_time = ""
        self.post_install = False
        self.post_install_detection = False
        self.post_install_detection_time = ""
        self.skip_installation = False
        self.applicability = False
        self.applicability_time = ""
        self.applicability_reason = ""
        self.filter_state = None
        self.extended_applicability = True
        self.extended_applicability_time = ""
        self.proxy_url = ""
        self.download_url = ""
        self.download_do_mode = ""  # Foreground 12 hours, Background 10 minutes
        self.download_start_time = ""
        self.download_finish_time = ""
        self.download_file_size = -1
        self.app_file_size = -1
        self.download_time = -1
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
        self.installer_timeout_str = ""
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
        self.applicability_state_json = ""
        self.detection_state_json = ""
        self.execution_state_json = ""
        self.reporting_state_json = ""

        self.msfb_detected_version = ""
        self.msfb_installed_version = ""
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
        'IN_PROGRESS_PENDING_MANAGED_INSTALLER': 2012,
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
                                 2009: 'IN_PROGRESS_CONTENT_DOWNLOADED', 2012: "IN_PROGRESS_PENDING_MANAGED_INSTALLER",
                                 2013: 'IN_PROGRESS_WAITING_USERLOGON',
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

    def convert_file_size_to_readable_string(self, size):
        if size > 1000000000:
            computed_size_str = str(
                (round(size / 1000000000, 2))) + ' GB'
        elif size > 1000000:
            computed_size_str = str(
                (round(size / 1000000, 2))) + ' MB'
        elif size > 1000:
            computed_size_str = str(
                (round(size / 1000, 2))) + ' KB'
        else:
            computed_size_str = str(
                round(size, 2)) + ' B'

        return computed_size_str

    def compute_download_size_and_speed(self):
        computed_size_str = 'Downloaded file size is: ' + self.convert_file_size_to_readable_string(
            self.download_file_size)

        computed_speed_str = 'Average download speed is: ' + self.download_average_speed

        return computed_size_str, computed_speed_str

    def convert_speedraw_to_string(self):
        download_average_speed_raw = -1
        if self.download_finish_time:
            download_finish_time = datetime.datetime.strptime(self.download_finish_time[:-4],
                                                              '%m-%d-%Y %H:%M:%S')
            download_start_time = datetime.datetime.strptime(self.download_start_time[:-4], '%m-%d-%Y %H:%M:%S')
            download_time_spent = (download_finish_time - download_start_time).total_seconds()
            if download_time_spent < self.download_time - 9:
                self.download_time = download_time_spent

        if self.download_time > 0 and self.download_file_size > 0:
            download_average_speed_raw = self.download_file_size * 1.0 / self.download_time
        elif not self.download_finish_time:
            print("No self.download_finish_time, exit in convert_speedraw_to_string")
            return ""
        else:
            download_finish_time = datetime.datetime.strptime(self.download_finish_time[:-4],
                                                              '%m-%d-%Y %H:%M:%S')
            download_start_time = datetime.datetime.strptime(self.download_start_time[:-4], '%m-%d-%Y %H:%M:%S')
            time_difference = (download_finish_time - download_start_time).total_seconds()
            if time_difference <= 0:
                print("download_finish_time = download_start_time, download not finished")
                self.download_success = False
                download_average_speed_raw = 0
            else:
                download_average_speed_raw = self.download_file_size * 1.0 / time_difference

        if download_average_speed_raw > 1000000:
            download_average_speed_converted = str(
                round(download_average_speed_raw / 1000000, 1)) + " MB/s"
        elif download_average_speed_raw > 1000:
            download_average_speed_converted = str(
                round(download_average_speed_raw / 1000, 1)) + " KB/s"
        else:
            download_average_speed_converted = str(round(download_average_speed_raw, 1)) + " B/s"
        return download_average_speed_converted

    def determine_no_enforcement_reason(self):
        if not self.grs_expiry:
            self.no_enforcement_reason = "Win32 app GRS is not expired."
        elif self.pre_install_detection and self.intent != 4:
            self.no_enforcement_reason = "Intent is install and app is detected."
        elif not self.pre_install_detection and self.intent == 4:
            self.no_enforcement_reason = "Intent is uninstall and app is not detected."
        elif not self.applicability:
            if self.applicability_reason != "":
                self.no_enforcement_reason = self.applicability_reason
                # self.applicability_reason = ""
                self.reason_need_output = False
        elif self.subgraph_type == 1:
            self.no_enforcement_reason = self.cur_enforcement_state
            self.reason_need_output = True
        elif self.subgraph_type == 2:
            if self.cur_enforcement_state == "IN_PROGRESS_PENDING_REBOOT":
                self.no_enforcement_reason = "App pending reboot."
            else:
                self.no_enforcement_reason = "Subgraph may be missing required intent in dependency chain."
            self.reason_need_output = True
        elif self.subgraph_type == 3:
            self.no_enforcement_reason = "Superseded app is not detected. No need to process."
            self.reason_need_output = True
        else:
            self.no_enforcement_reason = self.cur_enforcement_state
            self.reason_need_output = True

    def load_current_enforcement_state(self):
        if self.current_enforcement_status_report is not None:
            if self.current_enforcement_status_report['EnforcementState'] is not None:
                if self.current_enforcement_status_report['EnforcementState'] in self.enforcement_dict.keys():
                    self.cur_enforcement_state = self.enforcement_dict[
                        self.current_enforcement_status_report['EnforcementState']]
            else:
                # Fix a bug that Uninstallation enforcement state will be Null if not detected app. It is by design
                if self.intent == 4 and not self.pre_install_detection:
                    self.cur_enforcement_state = "SUCCEEDED"
        else:
            self.cur_enforcement_state = self.last_enforcement_state

    def load_last_enforcement_state(self):
        if self.last_enforcement_json is not None:
            if 'EnforcementState' in self.last_enforcement_json:
                if self.last_enforcement_json['EnforcementState'] is not None:
                    if self.last_enforcement_json['EnforcementState'] in self.enforcement_dict.keys():
                        self.last_enforcement_state = self.enforcement_dict[
                            self.last_enforcement_json['EnforcementState']]
                    else:
                        self.last_enforcement_state = self.last_enforcement_json['EnforcementState']
                else:
                    self.last_enforcement_state = "No enforcement state found"
            else:
                self.last_enforcement_state = "No enforcement state found"
        else:
            self.last_enforcement_state = "No enforcement state found"

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

    def interpret_app_log(self):
        if self.app_type == "MSFB":
            self.process_msfb_app_log()
        elif self.app_type == "Win32":
            if self.subgraph_type == 1:
                self.process_win32_standalone_app_log()
            elif self.subgraph_type == 2:
                self.process_win32_dependency_app_log()
            elif self.subgraph_type == 3:
                self.process_win32_supercedence_app_log()

    def process_win32_standalone_app_log(self):
        # if not self.grs_expiry:
        #     # skipped processing enforcement log due to GRS
        #     # Available app will skip GRS since user manually clicks install button in company portal
        #     return None
        post_install = False
        post_download = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = logprocessinglibrary.get_timestamp_by_line(cur_line)

            if cur_line.startswith(self.log_keyword_table['LOG_WIN32_DETECTION_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DETECTION_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(self.log_keyword_table['LOG_WIN32_DETECTION_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 8] == "Detected":
                        self.pre_install_detection = True
                        self.pre_install_detection_time = cur_time
                    else:
                        self.pre_install_detection = False
                        self.pre_install_detection_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DETECTION_STATE_REPORT_INDICATOR']):
                # Evaluating whether app has enforcement
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DETECTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                # Pre-Download Detection
                detection_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_DETECTION_STATE_JSON_INDICATOR'])
                detection_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[detection_state_json_start_index: detection_state_json_stop_index])
                # print(self.detection_state_json)
                if not post_download and not post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.pre_install_detection = True
                            self.pre_install_detection_time = cur_time
                        elif self.detection_state_json['DetectionState']['NewValue'] == "NotInstalled":
                            self.pre_install_detection = False
                            self.pre_install_detection_time = cur_time
                elif post_download and not post_install:
                    """
                    post download, pre-install detection.
                    Sometimes app gets detected after download.
                    """
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_download_detection = True
                            self.post_download_detection_time = cur_time
                            self.skip_installation = True
                elif post_download and post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_install_detection = True
                            self.post_install_detection_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(
                        self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 10] == "Applicable":
                        self.applicability = True
                        self.applicability_time = cur_time
                    else:
                        self.applicability = False
                        self.applicability_time = cur_time
            elif cur_line.startswith(
                    self.log_keyword_table['LOG_WIN32_APPLICABILITY_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                applicability_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_APPLICABILITY_STATE_JSON_INDICATOR'])
                applicability_state_json_stop_index = cur_line.find(
                    self.log_keyword_table['LOG_ENDING_STRING'])
                self.applicability_state_json = json.loads(
                    cur_line[applicability_state_json_start_index: applicability_state_json_stop_index])
                if self.applicability_state_json['ApplicabilityState']['NewValue'] == "Applicable":
                    self.applicability = True
                elif self.applicability_state_json['ApplicabilityState'][
                    'NewValue'] == "AppUnsupportedDueToUnknownReason":
                    self.applicability = False
                    self.applicability_reason = "User Context App will be processed after user logon."
                elif self.applicability_state_json['ApplicabilityState'][
                    'NewValue'] == "ScriptRequirementRuleNotMet":
                    self.applicability = False
                    self.applicability_reason = "Script Requirement Rule Not Met."
                else:
                    self.applicability = False
                self.applicability_time = cur_time

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXECUTION_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_EXECUTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue

                """
                In post Install detection, if app not detected, it will reflect in Execution report instead of Detection report.
                <![LOG[[Win32App] Completed detectionManager SideCarProductCodeDetectionManager, applicationDetectedByCurrentRule: False]LOG]!><time="20:48:53.4427411" date="10-16-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                <![LOG[[Win32App][ReportingManager] Execution state for app with id: 6ddfcc73-09da-4789-a4a5-b437b73906d7 has been updated. Report delta: {"EnforcementState":{"OldValue":"Success","NewValue":"Error"},"EnforcementErrorCode":{"OldValue":0,"NewValue":-2016345060}}]LOG]!><time="20:48:53.4442020" date="10-16-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                execution_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_EXECUTION_STATE_JSON_INDICATOR'])
                execution_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[execution_state_json_start_index: execution_state_json_stop_index])
                if post_download and post_install:
                    if self.detection_state_json['EnforcementState']['NewValue'] == "Error":
                        self.post_install_detection = False
                        self.post_install_detection_time = cur_time

            elif cur_line.startswith(
                    self.log_keyword_table['LOG_WIN32_NO_ACTION_REQUIRED_INDICATOR']):  # TODO ? Delete?
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue
                # Stop without enforcement
                self.has_enforcement = False
                self.cur_app_log_end_index = cur_line_index
                break
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOADING_START_INDICATOR']):
                """
                Win32 downloading start indicator

                <![LOG[[Win32App] Downloading app on session 2. App: 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]!><time="12:37:58.5140236" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, '. App: ')
                if cur_app_id != self.app_id:
                    continue
                if self.download_start_time == "":
                    self.download_start_time = cur_time
                self.has_enforcement = True
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_URL_LINE_INDICATOR']):
                download_url_start_index = len(self.log_keyword_table['LOG_WIN32_DOWNLOAD_URL_INDICATOR'])
                download_url_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                if self.download_url == "":
                    self.download_url = cur_line[download_url_start_index: download_url_stop_index]

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_PROXY_INDICATOR']):
                proxy_start_index = len(self.log_keyword_table['LOG_WIN32_PROXY_INDICATOR'])
                proxy_end_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.proxy_url = cur_line[proxy_start_index:proxy_end_index]
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_TIMEOUT_INDICATOR']):
                if cur_line.startswith(self.log_keyword_table[
                                           'LOG_WIN32_DO_BG_TIMEOUT_INDICATOR']):  # code update to allow DO background time out to 30 min instead of 10 min
                    if self.download_do_mode == "" and self.pre_install_detection_time != "":
                        self.download_do_mode = "BACKGROUND(30 min timeout)"
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_FG_TIMEOUT_INDICATOR']):
                    if self.download_do_mode == "" and self.pre_install_detection_time != "":
                        self.download_do_mode = "FOREGROUND(12 hour timeout)"
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOADING_PROGRESS_INDICATOR']):
                """
                Track downloaded size in case timeout.

                <![LOG[[StatusService] Downloading app (id = e765119c-6af3-4d39-8eac-3e86fd7642b0, name Adobe Acrobat DC) via DO, bytes 720928912/721977488 for user 37ed0412-d13e-481c-a784-6447007aa208]LOG]!><time="09:49:19.3750179" date="10-26-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">                
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DOWNLOADING_PROGRESS_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                downloaded_size_index_start = cur_line.find(self.log_keyword_table[
                                                                'LOG_WIN32_DOWNLOADED_START_INDICATOR']) + \
                                              len(self.log_keyword_table['LOG_WIN32_DOWNLOADED_START_INDICATOR'])
                downloaded_size_index_stop = cur_line.find(
                    self.log_keyword_table['LOG_WIN32_DOWNLOADED_STOP_INDICATOR'])
                percent_size = cur_line[downloaded_size_index_start: downloaded_size_index_stop].split('/')
                downloaded_size = int(percent_size[0])
                app_size = int(percent_size[1])
                self.download_file_size = downloaded_size
                if self.app_file_size <= 0:
                    self.app_file_size = app_size

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_FINISH_INDICATOR']):
                if self.download_finish_time == "" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = True
                    post_download = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_NOT_FINISH_INDICATOR']):
                if self.download_finish_time == "" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = False
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CDN_START_INDICATOR']):
                """
                DO mode failed and switched to CDN mode

                <![LOG[[Win32App] ExternalCDN mode, content raw URL is http://swdc02-mscdn.manage.microsoft.com/9f5567be-61f6-471a-aa19-c861288bbeb6/7b67a1bc-58f6-4d45-bb3a-d1035fe0e897/d85339f0-1e76-4c3d-ba03-b82216aff5ec.intunewin.bin]LOG]!><time="15:38:38.0738644" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="10" file="">
                <![LOG[[StatusService] Downloading app (id = 22ccfbac-0e48-43e2-960d-ada16559ed33, name Autopilot Branding) via CDN, bytes 21524/64425536 for user 00000000-0000-0000-0000-000000000000]LOG]!><time="15:38:38.1446607" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App] CDN mode, download completes.]LOG]!><time="15:38:43.2381585" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="10" file="">

                """
                if self.download_url in cur_line:
                    self.download_start_time = cur_time
                    self.download_do_mode = "CDN mode"
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CDN_STOP_INDICATOR']):
                if self.download_do_mode == "CDN mode" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = True
                    post_download = True
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CONTENT_CACHED_INDICATOR']):
                """
                Added scenario where content is cached, no need to download
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_CONTENT_CACHED_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                self.has_enforcement = True
                self.download_success = True
                self.download_finish_time = cur_time
                post_download = True
            # TODO: CDN failure scenario?
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_HASH_SUCCESS_INDICATOR']):
                if self.hash_validate_success_time == "":
                    self.hash_validate_success_time = cur_time
                    self.hash_validate_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DECRYPT_SUCCESS_INDICATOR']):
                if self.decryption_success_time == "":
                    self.decryption_success_time = cur_time
                    self.decryption_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_SIZE_INDICATOR']):
                file_size_index_start = 38
                file_size_index_end = cur_line.find(']LOG]!') - 3
                self.download_file_size = int(
                    (cur_line[file_size_index_start:file_size_index_end]).replace(',', ''))

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_TIME_INDICATOR']):
                download_time_index_start = len(self.log_keyword_table['LOG_WIN32_DOWNLOAD_TIME_INDICATOR'])
                download_time_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 3
                self.download_time = int(
                    (cur_line[download_time_index_start:download_time_index_stop]).replace(',', '')) // 1000
                # print(self.detection_state_json)
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CLEANUP_INDICATOR']):
                if self.unzipping_success_time == "":
                    self.unzipping_success_time = cur_time
                    self.unzipping_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXECUTE_INDICATOR']):
                if self.current_attempt_num == "0":
                    self.current_attempt_num = cur_line[42:43] + '1'
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_CREATE_INDICATOR']):
                if self.install_start_time == "":
                    self.install_start_time = cur_time
                    self.installer_created_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_ID_INDICATOR']):
                installer_thread_id_index_start = cur_line.find('process id = ') + len('process id = ')
                installer_thread_id_index_stop = cur_line.find(']LOG]!')
                if self.installer_thread_id == "":
                    self.installer_thread_id = \
                        cur_line[installer_thread_id_index_start:installer_thread_id_index_stop]
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR']):
                timeout_index_start = cur_line.find(
                    self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR']) + \
                                      len(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR'])
                timeout_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1
                time_str_raw = cur_line[timeout_index_start: timeout_index_stop]
                self.installer_timeout_str = str(int(int(time_str_raw) / 1000 / 60))
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_FINISH_INDICATOR']):
                if self.install_finish_time == "":
                    self.install_finish_time = cur_time
                    post_install = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_INDICATOR']):

                if cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_DEF_INDICATOR']):
                    installation_result_index_start = len(
                        self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_DEF_INDICATOR'])
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
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXIT_CODE_NOMAPPING_INDICATOR']):
                installation_result_index_start = len('<![LOG[[Win32App] ')
                installation_result_index_stop = cur_line.find('of app: ')
                if self.installation_result == "":
                    self.installer_exit_success = True
                    self.installation_result = \
                        cur_line[installation_result_index_start:installation_result_index_stop]
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_REPORTING_STATE_INDICATOR']):
                cur_enforcement_index_start = cur_line.find('{"ApplicationId"')
                cur_enforcement_index_end = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_REPORTING_STATE_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                app_json = cur_line[cur_enforcement_index_start:cur_enforcement_index_end]
                try:
                    temp_enforcement_report = json.loads(app_json)
                    self.current_enforcement_status_report = temp_enforcement_report
                except ValueError:
                    print("Json invalid, dropping")

        if self.download_start_time != "":
            self.download_average_speed = self.convert_speedraw_to_string()

    def process_win32_dependency_app_log(self):
        # if not self.grs_expiry:
        #     # skipped processing enforcement log due to GRS
        #     return None
        post_install = False
        post_download = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = logprocessinglibrary.get_timestamp_by_line(cur_line)

            if cur_line.startswith(self.log_keyword_table['LOG_WIN32_DETECTION_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DETECTION_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(self.log_keyword_table['LOG_WIN32_DETECTION_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 8] == "Detected":
                        self.pre_install_detection = True
                        self.pre_install_detection_time = cur_time
                    else:
                        self.pre_install_detection = False
                        self.pre_install_detection_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DETECTION_STATE_REPORT_INDICATOR']):
                # Evaluating whether app has enforcement
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DETECTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                # Pre-Download Detection
                detection_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_DETECTION_STATE_JSON_INDICATOR'])
                detection_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[detection_state_json_start_index: detection_state_json_stop_index])
                # print(self.detection_state_json)
                if not post_download and not post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.pre_install_detection = True
                            self.pre_install_detection_time = cur_time
                        elif self.detection_state_json['DetectionState']['NewValue'] == "NotInstalled":
                            self.pre_install_detection = False
                            self.pre_install_detection_time = cur_time
                        elif self.detection_state_json['DetectionState']['NewValue'] == "Undetectable":
                            # Root app in dependency chain will not be detected before dependent apps are detected and processed
                            self.pre_install_detection = False
                            self.pre_install_detection_time = cur_time
                elif post_download and not post_install:
                    """
                    post download, pre-install detection.
                    Sometimes app gets detected after download.
                    """
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_download_detection = True
                            self.post_download_detection_time = cur_time
                            self.skip_installation = True
                elif post_download and post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_install_detection = True
                            self.post_install_detection_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(
                        self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 10] == "Applicable":
                        self.applicability = True
                        self.applicability_time = cur_time
                    else:
                        self.applicability = False
                        self.applicability_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_APPLICABILITY_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                applicability_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_APPLICABILITY_STATE_JSON_INDICATOR'])
                applicability_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.applicability_state_json = json.loads(
                    cur_line[applicability_state_json_start_index: applicability_state_json_stop_index])
                if self.applicability_state_json['ApplicabilityState']['NewValue'] == "Applicable":
                    self.applicability = True
                elif self.applicability_state_json['ApplicabilityState'][
                    'NewValue'] == "AppUnsupportedDueToUnknownReason":
                    self.applicability = False
                    self.applicability_reason = "User Context App will be processed after user logon."
                else:
                    self.applicability = False
                self.applicability_time = cur_time

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXECUTION_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_EXECUTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue

                """
                In post Install detection, if app not detected, it will reflect in Execution report instead of Detection report.
                <![LOG[[Win32App] Completed detectionManager SideCarProductCodeDetectionManager, applicationDetectedByCurrentRule: False]LOG]!><time="20:48:53.4427411" date="10-16-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                <![LOG[[Win32App][ReportingManager] Execution state for app with id: 6ddfcc73-09da-4789-a4a5-b437b73906d7 has been updated. Report delta: {"EnforcementState":{"OldValue":"Success","NewValue":"Error"},"EnforcementErrorCode":{"OldValue":0,"NewValue":-2016345060}}]LOG]!><time="20:48:53.4442020" date="10-16-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                execution_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_EXECUTION_STATE_JSON_INDICATOR'])
                execution_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[execution_state_json_start_index: execution_state_json_stop_index])
                if post_download and post_install:
                    if self.detection_state_json['EnforcementState']['NewValue'] == "Error":
                        self.post_install_detection = False
                        self.post_install_detection_time = cur_time

            elif cur_line.startswith(
                    self.log_keyword_table['LOG_WIN32_NO_ACTION_REQUIRED_INDICATOR']):  # TODO ? Delete?
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue
                # Stop without enforcement
                self.has_enforcement = False
                self.cur_app_log_end_index = cur_line_index
                break
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOADING_START_INDICATOR']):
                """
                Win32 downloading start indicator

                <![LOG[[Win32App] Downloading app on session 2. App: 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]!><time="12:37:58.5140236" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, '. App: ')
                if cur_app_id != self.app_id:
                    continue
                if self.download_start_time == "":
                    self.download_start_time = cur_time
                self.has_enforcement = True
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_URL_LINE_INDICATOR']):
                download_url_start_index = len(self.log_keyword_table['LOG_WIN32_DOWNLOAD_URL_INDICATOR'])
                download_url_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                if self.download_url == "":
                    self.download_url = cur_line[download_url_start_index: download_url_stop_index]

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_PROXY_INDICATOR']):
                proxy_start_index = len(self.log_keyword_table['LOG_WIN32_PROXY_INDICATOR'])
                proxy_end_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.proxy_url = cur_line[proxy_start_index:proxy_end_index]
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_TIMEOUT_INDICATOR']):
                if cur_line.startswith(self.log_keyword_table[
                                           'LOG_WIN32_DO_BG_TIMEOUT_INDICATOR']):  # code update to allow DO background time out to 30 min instead of 10 min
                    if self.download_do_mode == "" and self.pre_install_detection_time != "":
                        self.download_do_mode = "BACKGROUND(30 min timeout)"
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_FG_TIMEOUT_INDICATOR']):
                    if self.download_do_mode == "" and self.pre_install_detection_time != "":
                        self.download_do_mode = "FOREGROUND(12 hour timeout)"
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOADING_PROGRESS_INDICATOR']):
                """
                Track downloaded size in case timeout.
                
                <![LOG[[StatusService] Downloading app (id = e765119c-6af3-4d39-8eac-3e86fd7642b0, name Adobe Acrobat DC) via DO, bytes 720928912/721977488 for user 37ed0412-d13e-481c-a784-6447007aa208]LOG]!><time="09:49:19.3750179" date="10-26-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">                
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DOWNLOADING_PROGRESS_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                downloaded_size_index_start = cur_line.find(self.log_keyword_table[
                                                                'LOG_WIN32_DOWNLOADED_START_INDICATOR']) + \
                                              len(self.log_keyword_table['LOG_WIN32_DOWNLOADED_START_INDICATOR'])
                downloaded_size_index_stop = cur_line.find(
                    self.log_keyword_table['LOG_WIN32_DOWNLOADED_STOP_INDICATOR'])
                percent_size = cur_line[downloaded_size_index_start: downloaded_size_index_stop].split('/')
                downloaded_size = int(percent_size[0])
                app_size = int(percent_size[1])
                self.download_file_size = downloaded_size
                if self.app_file_size <= 0:
                    self.app_file_size = app_size

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_FINISH_INDICATOR']):
                if self.has_enforcement:
                    if self.download_finish_time == "" and self.download_start_time != "":
                        self.download_finish_time = cur_time
                        self.download_success = True
                        post_download = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_NOT_FINISH_INDICATOR']):
                if self.download_finish_time == "" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = False
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CDN_START_INDICATOR']):
                """
                DO mode failed and switched to CDN mode

                <![LOG[[Win32App] ExternalCDN mode, content raw URL is http://swdc02-mscdn.manage.microsoft.com/9f5567be-61f6-471a-aa19-c861288bbeb6/7b67a1bc-58f6-4d45-bb3a-d1035fe0e897/d85339f0-1e76-4c3d-ba03-b82216aff5ec.intunewin.bin]LOG]!><time="15:38:38.0738644" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="10" file="">
                <![LOG[[StatusService] Downloading app (id = 22ccfbac-0e48-43e2-960d-ada16559ed33, name Autopilot Branding) via CDN, bytes 21524/64425536 for user 00000000-0000-0000-0000-000000000000]LOG]!><time="15:38:38.1446607" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App] CDN mode, download completes.]LOG]!><time="15:38:43.2381585" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="10" file="">

                """
                if self.download_url in cur_line:
                    self.download_start_time = cur_time
                    self.download_do_mode = "CDN mode"
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CDN_STOP_INDICATOR']):
                if self.download_do_mode == "CDN mode" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = True
                    post_download = True

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CONTENT_CACHED_INDICATOR']):
                """
                Added scenario where content is cached, no need to download
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_CONTENT_CACHED_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                self.has_enforcement = True
                self.download_success = True
                self.download_finish_time = cur_time
                post_download = True
                # TODO: CDN failure scenario?
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_HASH_SUCCESS_INDICATOR']):
                if self.has_enforcement:
                    if self.hash_validate_success_time == "":
                        self.hash_validate_success_time = cur_time
                        self.hash_validate_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DECRYPT_SUCCESS_INDICATOR']):
                if self.has_enforcement:
                    if self.decryption_success_time == "":
                        self.decryption_success_time = cur_time
                        self.decryption_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_SIZE_INDICATOR']):
                file_size_index_start = 38
                file_size_index_end = cur_line.find(']LOG]!') - 3
                self.download_file_size = int(
                    (cur_line[file_size_index_start:file_size_index_end]).replace(',', ''))

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_TIME_INDICATOR']):
                download_time_index_start = len(self.log_keyword_table['LOG_WIN32_DOWNLOAD_TIME_INDICATOR'])
                download_time_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 3
                self.download_time = int(
                    (cur_line[download_time_index_start:download_time_index_stop]).replace(',', '')) // 1000
                # print(self.detection_state_json)
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CLEANUP_INDICATOR']):
                if self.has_enforcement:
                    if self.unzipping_success_time == "":
                        self.unzipping_success_time = cur_time
                        self.unzipping_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXECUTE_INDICATOR']):
                if self.current_attempt_num == "0":
                    self.current_attempt_num = cur_line[42:43] + '1'
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_CREATE_INDICATOR']):
                if self.install_start_time == "":
                    self.install_start_time = cur_time
                    self.installer_created_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_ID_INDICATOR']):
                installer_thread_id_index_start = cur_line.find('process id = ') + len('process id = ')
                installer_thread_id_index_stop = cur_line.find(']LOG]!')
                if self.installer_thread_id == "":
                    self.installer_thread_id = \
                        cur_line[installer_thread_id_index_start:installer_thread_id_index_stop]
                else:
                    continue  # Means this is the line for other dependent apps

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR']):
                timeout_index_start = cur_line.find(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR']) + \
                                      len(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR'])
                timeout_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1
                time_str_raw = cur_line[timeout_index_start: timeout_index_stop]
                self.installer_timeout_str = str(int(int(time_str_raw)/1000/60))
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_FINISH_INDICATOR']):
                if self.install_finish_time == "":
                    self.install_finish_time = cur_time
                    post_install = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_INDICATOR']):

                if cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_DEF_INDICATOR']):
                    installation_result_index_start = len(
                        self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_DEF_INDICATOR'])
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
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXIT_CODE_NOMAPPING_INDICATOR']):
                installation_result_index_start = len('<![LOG[[Win32App] ')
                installation_result_index_stop = cur_line.find('of app: ')
                if self.installation_result == "":
                    self.installer_exit_success = True
                    self.installation_result = \
                        cur_line[installation_result_index_start:installation_result_index_stop]
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_REPORTING_STATE_INDICATOR']):
                cur_enforcement_index_start = cur_line.find('{"ApplicationId"')
                cur_enforcement_index_end = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_REPORTING_STATE_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                app_json = cur_line[cur_enforcement_index_start:cur_enforcement_index_end]
                try:
                    temp_enforcement_report = json.loads(app_json)
                    self.current_enforcement_status_report = temp_enforcement_report
                except ValueError:
                    print("Json invalid, dropping")
        if self.download_start_time != "":
            self.download_average_speed = self.convert_speedraw_to_string()

    def process_win32_supercedence_app_log(self):
        post_install = False
        post_download = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = logprocessinglibrary.get_timestamp_by_line(cur_line)

            if cur_line.startswith(self.log_keyword_table['LOG_WIN32_DETECTION_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DETECTION_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(self.log_keyword_table['LOG_WIN32_DETECTION_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 8] == "Detected":
                        self.pre_install_detection = True
                        self.pre_install_detection_time = cur_time
                    else:
                        self.pre_install_detection = False
                        self.pre_install_detection_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DETECTION_STATE_REPORT_INDICATOR']):
                # Evaluating whether app has enforcement
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DETECTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                # Pre-Download Detection
                detection_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_DETECTION_STATE_JSON_INDICATOR'])
                detection_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[detection_state_json_start_index: detection_state_json_stop_index])
                # print(self.detection_state_json)
                if not post_download and not post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.pre_install_detection = True
                            self.pre_install_detection_time = cur_time
                        elif self.detection_state_json['DetectionState']['NewValue'] == "NotInstalled":
                            self.pre_install_detection = False
                            self.pre_install_detection_time = cur_time
                        elif self.detection_state_json['DetectionState']['NewValue'] == "Undetectable":
                            # Root app in dependency chain will not be detected before dependent apps are detected and processed
                            self.pre_install_detection = False
                            self.pre_install_detection_time = cur_time
                elif post_download and not post_install:
                    """
                    post download, pre-install detection.
                    Sometimes app gets detected after download.
                    """
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_download_detection = True
                            self.post_download_detection_time = cur_time
                            self.skip_installation = True
                elif post_download and post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_install_detection = True
                            self.post_install_detection_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(
                        self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 10] == "Applicable":
                        self.applicability = True
                        self.applicability_time = cur_time
                    else:
                        self.applicability = False
                        self.applicability_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_APPLICABILITY_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                applicability_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_APPLICABILITY_STATE_JSON_INDICATOR'])
                applicability_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.applicability_state_json = json.loads(
                    cur_line[applicability_state_json_start_index: applicability_state_json_stop_index])
                if self.applicability_state_json['ApplicabilityState']['NewValue'] == "Applicable":
                    self.applicability = True
                elif self.applicability_state_json['ApplicabilityState'][
                    'NewValue'] == "AppUnsupportedDueToUnknownReason":
                    self.applicability = False
                    self.applicability_reason = "User Context App will be processed after user logon."
                else:
                    self.applicability = False
                self.applicability_time = cur_time

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXECUTION_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_EXECUTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue

                """
                In post Install detection, if app not detected, it will reflect in Execution report instead of Detection report.
                <![LOG[[Win32App] Completed detectionManager SideCarProductCodeDetectionManager, applicationDetectedByCurrentRule: False]LOG]!><time="20:48:53.4427411" date="10-16-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                <![LOG[[Win32App][ReportingManager] Execution state for app with id: 6ddfcc73-09da-4789-a4a5-b437b73906d7 has been updated. Report delta: {"EnforcementState":{"OldValue":"Success","NewValue":"Error"},"EnforcementErrorCode":{"OldValue":0,"NewValue":-2016345060}}]LOG]!><time="20:48:53.4442020" date="10-16-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                execution_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_EXECUTION_STATE_JSON_INDICATOR'])
                execution_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[execution_state_json_start_index: execution_state_json_stop_index])
                if post_download and post_install:
                    if self.detection_state_json['EnforcementState']['NewValue'] == "Error":
                        self.post_install_detection = False
                        self.post_install_detection_time = cur_time

            elif cur_line.startswith(
                    self.log_keyword_table['LOG_WIN32_NO_ACTION_REQUIRED_INDICATOR']):  # TODO ? Delete?
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, "app with id: ")
                if cur_app_id != self.app_id:
                    continue
                # Stop without enforcement
                self.has_enforcement = False
                self.cur_app_log_end_index = cur_line_index
                break
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOADING_START_INDICATOR']):
                """
                Win32 downloading start indicator

                <![LOG[[Win32App] Downloading app on session 2. App: 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]!><time="12:37:58.5140236" date="3-23-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, '. App: ')
                if cur_app_id != self.app_id:
                    continue
                if self.download_start_time == "":
                    self.download_start_time = cur_time
                self.has_enforcement = True
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_URL_LINE_INDICATOR']):
                download_url_start_index = len(self.log_keyword_table['LOG_WIN32_DOWNLOAD_URL_INDICATOR'])
                download_url_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                if self.download_url == "":
                    self.download_url = cur_line[download_url_start_index: download_url_stop_index]

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_PROXY_INDICATOR']):
                proxy_start_index = len(self.log_keyword_table['LOG_WIN32_PROXY_INDICATOR'])
                proxy_end_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.proxy_url = cur_line[proxy_start_index:proxy_end_index]
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_TIMEOUT_INDICATOR']):
                if cur_line.startswith(self.log_keyword_table[
                                           'LOG_WIN32_DO_BG_TIMEOUT_INDICATOR']):  # code update to allow DO background time out to 30 min instead of 10 min
                    if self.download_do_mode == "" and self.pre_install_detection_time != "":
                        self.download_do_mode = "BACKGROUND(30 min timeout)"
                    else:
                        continue  # Means this is the line for other dependent apps
                elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_FG_TIMEOUT_INDICATOR']):
                    if self.download_do_mode == "" and self.pre_install_detection_time != "":
                        self.download_do_mode = "FOREGROUND(12 hour timeout)"
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOADING_PROGRESS_INDICATOR']):
                """
                Track downloaded size in case timeout.

                <![LOG[[StatusService] Downloading app (id = e765119c-6af3-4d39-8eac-3e86fd7642b0, name Adobe Acrobat DC) via DO, bytes 720928912/721977488 for user 37ed0412-d13e-481c-a784-6447007aa208]LOG]!><time="09:49:19.3750179" date="10-26-2023" component="IntuneManagementExtension" context="" type="1" thread="5" file="">                
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_DOWNLOADING_PROGRESS_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                downloaded_size_index_start = cur_line.find(self.log_keyword_table[
                                                                'LOG_WIN32_DOWNLOADED_START_INDICATOR']) + \
                                              len(self.log_keyword_table['LOG_WIN32_DOWNLOADED_START_INDICATOR'])
                downloaded_size_index_stop = cur_line.find(
                    self.log_keyword_table['LOG_WIN32_DOWNLOADED_STOP_INDICATOR'])
                percent_size = cur_line[downloaded_size_index_start: downloaded_size_index_stop].split('/')
                downloaded_size = int(percent_size[0])
                app_size = int(percent_size[1])
                self.download_file_size = downloaded_size
                if self.app_file_size <= 0:
                    self.app_file_size = app_size

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_FINISH_INDICATOR']):
                if self.has_enforcement:
                    if self.download_finish_time == "" and self.download_start_time != "":
                        self.download_finish_time = cur_time
                        self.download_success = True
                        post_download = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DO_NOT_FINISH_INDICATOR']):
                if self.download_finish_time == "" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = False
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CDN_START_INDICATOR']):
                """
                DO mode failed and switched to CDN mode

                <![LOG[[Win32App] ExternalCDN mode, content raw URL is http://swdc02-mscdn.manage.microsoft.com/9f5567be-61f6-471a-aa19-c861288bbeb6/7b67a1bc-58f6-4d45-bb3a-d1035fe0e897/d85339f0-1e76-4c3d-ba03-b82216aff5ec.intunewin.bin]LOG]!><time="15:38:38.0738644" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="10" file="">
                <![LOG[[StatusService] Downloading app (id = 22ccfbac-0e48-43e2-960d-ada16559ed33, name Autopilot Branding) via CDN, bytes 21524/64425536 for user 00000000-0000-0000-0000-000000000000]LOG]!><time="15:38:38.1446607" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App] CDN mode, download completes.]LOG]!><time="15:38:43.2381585" date="10-23-2023" component="IntuneManagementExtension" context="" type="1" thread="10" file="">

                """
                if self.download_url in cur_line:
                    self.download_start_time = cur_time
                    self.download_do_mode = "CDN mode"
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CDN_STOP_INDICATOR']):
                if self.download_do_mode == "CDN mode" and self.download_start_time != "":
                    self.download_finish_time = cur_time
                    self.download_success = True
                    post_download = True
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CONTENT_CACHED_INDICATOR']):
                """
                Added scenario where content is cached, no need to download
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_CONTENT_CACHED_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                self.has_enforcement = True
                self.download_success = True
                self.download_finish_time = cur_time
                post_download = True

                # TODO: CDN failure scenario?
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_HASH_SUCCESS_INDICATOR']):
                if self.has_enforcement:
                    if self.hash_validate_success_time == "":
                        self.hash_validate_success_time = cur_time
                        self.hash_validate_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DECRYPT_SUCCESS_INDICATOR']):
                if self.has_enforcement:
                    if self.decryption_success_time == "":
                        self.decryption_success_time = cur_time
                        self.decryption_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_SIZE_INDICATOR']):
                file_size_index_start = 38
                file_size_index_end = cur_line.find(']LOG]!') - 3
                self.download_file_size = int(
                    (cur_line[file_size_index_start:file_size_index_end]).replace(',', ''))

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_DOWNLOAD_TIME_INDICATOR']):
                download_time_index_start = len(self.log_keyword_table['LOG_WIN32_DOWNLOAD_TIME_INDICATOR'])
                download_time_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 3
                self.download_time = int(
                    (cur_line[download_time_index_start:download_time_index_stop]).replace(',', '')) // 1000
                # print(self.detection_state_json)
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_CLEANUP_INDICATOR']):
                if self.has_enforcement:
                    if self.unzipping_success_time == "":
                        self.unzipping_success_time = cur_time
                        self.unzipping_success = True
                    else:
                        continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXECUTE_INDICATOR']):
                if self.current_attempt_num == "0":
                    self.current_attempt_num = cur_line[42:43] + '1'
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_CREATE_INDICATOR']):
                if self.install_start_time == "":
                    self.install_start_time = cur_time
                    self.installer_created_success = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_ID_INDICATOR']):
                installer_thread_id_index_start = cur_line.find('process id = ') + len('process id = ')
                installer_thread_id_index_stop = cur_line.find(']LOG]!')
                if self.installer_thread_id == "":
                    self.installer_thread_id = \
                        cur_line[installer_thread_id_index_start:installer_thread_id_index_stop]
                else:
                    continue  # Means this is the line for other dependent apps

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR']):
                timeout_index_start = cur_line.find(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR']) + \
                                      len(self.log_keyword_table['LOG_WIN32_INSTALLER_TIMEOUT_INDICATOR'])
                timeout_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1
                time_str_raw = cur_line[timeout_index_start: timeout_index_stop]
                self.installer_timeout_str = str(int(int(time_str_raw) / 1000 / 60))
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_FINISH_INDICATOR']):
                if self.install_finish_time == "":
                    self.install_finish_time = cur_time
                    post_install = True
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_INDICATOR']):

                if cur_line.startswith(self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_DEF_INDICATOR']):
                    installation_result_index_start = len(
                        self.log_keyword_table['LOG_WIN32_INSTALL_EXIT_CODE_DEF_INDICATOR'])
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
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_EXIT_CODE_NOMAPPING_INDICATOR']):
                installation_result_index_start = len('<![LOG[[Win32App] ')
                installation_result_index_stop = cur_line.find('of app: ')
                if self.installation_result == "":
                    self.installer_exit_success = True
                    self.installation_result = \
                        cur_line[installation_result_index_start:installation_result_index_stop]
                else:
                    continue  # Means this is the line for other dependent apps
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_REPORTING_STATE_INDICATOR']):
                cur_enforcement_index_start = cur_line.find('{"ApplicationId"')
                cur_enforcement_index_end = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_REPORTING_STATE_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                app_json = cur_line[cur_enforcement_index_start:cur_enforcement_index_end]
                try:
                    temp_enforcement_report = json.loads(app_json)
                    self.current_enforcement_status_report = temp_enforcement_report
                except ValueError:
                    print("Json invalid, dropping")
        if self.download_start_time != "":
            self.download_average_speed = self.convert_speedraw_to_string()

    def process_msfb_user_context_app_log(self):
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = logprocessinglibrary.get_timestamp_by_line(cur_line)
            if cur_line.startswith(self.log_keyword_table['LOG_MSFB_USER_EXECUTING_START_INDICATOR']):
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

    def process_msfb_system_context_app_log(self):
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
            cur_time = logprocessinglibrary.get_timestamp_by_line(cur_line)
            if cur_line.startswith(self.log_keyword_table["LOG_MSFB_DOWNLOAD_SIZE_INDICATOR"]):
                size_need_to_download_index_start = len(self.log_keyword_table["LOG_MSFB_DOWNLOAD_SIZE_INDICATOR"])
                size_need_to_download_index_end = cur_line.find('BytesDownloaded - ')
                self.size_need_to_download = int(
                    cur_line[size_need_to_download_index_start:size_need_to_download_index_end])
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
                if cur_line[download_progress_index_start:download_progress_index_end] == '1' and int(
                        cur_line[size_downloaded_index_start:size_downloaded_index_end]) > 0:
                    self.download_file_size = int(cur_line[size_downloaded_index_start:size_downloaded_index_end])

    def process_msfb_app_log(self):
        """
        GRS not expired but SubGraph expired will process pre-detection and applicability
        """
        # if not self.grs_expiry:
        #     return None
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

        post_download = False
        post_install = False
        for cur_line_index in range(len(self.full_log)):
            cur_line = self.full_log[cur_line_index]
            cur_time = logprocessinglibrary.get_timestamp_by_line(cur_line)
            if cur_line.startswith(self.log_keyword_table['LOG_REPORTING_STATE_1_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_REPORTING_STATE_1_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if 'has both detection and applicability errors' in cur_line:
                    applicability_error_code_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_APPLICABILITY_ERROR_CODE_INDICATOR']) + \
                                                           len(self.log_keyword_table[
                                                                   'LOG_MSFB_APPLICABILITY_ERROR_CODE_INDICATOR'])
                    applicability_error_code_index_stop = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                    applicability_error_code = cur_line[
                                               applicability_error_code_index_start: applicability_error_code_index_stop - 1]
                    if applicability_error_code == "-2146233079":
                        self.applicability_reason = "Network Issue when trying to Invoke WinGet command. Try removing Proxy/Firewall or switch to different network."
                        self.applicability = False
                        self.applicability_time = cur_time
                        self.has_enforcement = False
            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_DETECTION_STATE_REPORT_INDICATOR']):
                # Evaluating whether app has enforcement
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_MSFB_DETECTION_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue

                # Pre-Download Detection
                detection_state_json_start_index = len(
                    self.log_keyword_table['LOG_MSFB_DETECTION_STATE_JSON_INDICATOR'])
                detection_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.detection_state_json = json.loads(
                    cur_line[detection_state_json_start_index: detection_state_json_stop_index])
                # print(self.detection_state_json)
                if not post_download and not post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        if 'DetectionErrorOccurred' in self.detection_state_json and 'DetectionErrorCode' in self.detection_state_json:
                            if self.detection_state_json['DetectionErrorOccurred']['NewValue'] == True:
                                if self.detection_state_json['DetectionErrorCode']['NewValue'] == -2146233079:
                                    self.pre_install_detection_time = cur_time
                                    self.pre_install_detection = False
                    elif self.pre_install_detection_time != "":
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.pre_install_detection = True
                            self.pre_install_detection_time = cur_time
                        elif self.detection_state_json['DetectionState']['NewValue'] == "NotInstalled":
                            self.pre_install_detection = False
                            self.pre_install_detection_time = cur_time
                # elif post_download and not post_install:
                #     """
                #     post download, pre-install detection.
                #     Sometimes app gets detected after download.
                #     """
                #     if 'DetectionState' not in self.detection_state_json:
                #         continue
                #     else:
                #         if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                #             self.post_download_detection = True
                #             self.post_download_detection_time = cur_time
                #             self.skip_installation = True
                elif post_download and post_install:
                    if 'DetectionState' not in self.detection_state_json:
                        continue
                    elif self.post_install_detection_time != "":
                        continue
                    else:
                        if self.detection_state_json['DetectionState']['NewValue'] == "Installed":
                            self.post_install_detection = True
                            self.post_install_detection_time = cur_time
                            if 'DetectedIdentityVersion' in self.detection_state_json:
                                self.msfb_detected_version = self.detection_state_json['DetectedIdentityVersion'][
                                    'NewValue']
                        elif self.detection_state_json['DetectionState']['NewValue'] == "NotInstalled":
                            self.post_install_detection = False
                            self.post_install_detection_time = cur_time

            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_FINISH_DETECTION_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_MSFB_FINISH_DETECTION_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    """
                    In Non-1st IME check in, MSFB app will not have ReportManager keyword to track detection and applicability check results.
                    Hence only can check from WinGetAppApplicabilityExecutor and WinGetAppDetectionExecutor
                    """

                    detected_state_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MFSB_DETECTION_DETECTED_INDICATOR']) + len(
                        self.log_keyword_table['LOG_MFSB_DETECTION_DETECTED_INDICATOR'])
                    detected_state_index_stop = cur_line.find(
                        self.log_keyword_table['LOG_MFSB_DETECTION_DETECTED_VERSION_INDICATOR']) - 3
                    if cur_line[detected_state_index_start:detected_state_index_stop] == "Detected":
                        self.pre_install_detection = True
                        self.pre_install_detection_time = cur_time
                        # self.has_enforcement = False
                    else:
                        self.pre_install_detection = False
                        self.pre_install_detection_time = cur_time
                    detected_version_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MFSB_DETECTION_DETECTED_VERSION_INDICATOR']) + len(
                        self.log_keyword_table['LOG_MFSB_DETECTION_DETECTED_VERSION_INDICATOR'])
                    detected_version_index_stop = cur_line.find(
                        self.log_keyword_table['LOG_MFSB_DETECTION_ERRORCODE_INDICATOR']) - 3
                    self.msfb_detected_version = cur_line[detected_version_index_start:detected_version_index_stop]

                    install_version_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_DETECTION_INSTALLED_VERSION_INDICATOR']) + len(
                        self.log_keyword_table['LOG_MSFB_DETECTION_INSTALLED_VERSION_INDICATOR'])
                    install_version_index_stop = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_DETECTION_REBOOT_INDICATOR']) - 3
                    self.msfb_installed_version = cur_line[install_version_index_start:install_version_index_stop]
                elif post_download and post_install:
                    install_version_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_DETECTION_INSTALLED_VERSION_INDICATOR']) + len(
                        self.log_keyword_table['LOG_MSFB_DETECTION_INSTALLED_VERSION_INDICATOR'])
                    install_version_index_stop = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_DETECTION_REBOOT_INDICATOR']) - 3
                    self.msfb_installed_version = cur_line[install_version_index_start:install_version_index_stop]

            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_APPLICABILITY_OLD_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                if not post_download and not post_install:
                    detection_old_start_index = len(
                        self.log_keyword_table['LOG_WIN32_APPLICABILITY_OLD_RESULT_INDICATOR'])
                    if cur_line[detection_old_start_index:detection_old_start_index + 10] == "Applicable":
                        self.applicability = True
                        self.applicability_time = cur_time
                    else:
                        self.applicability = False
                        self.applicability_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_APPLICABILITY_STATE_REPORT_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_MSFB_APPLICABILITY_STATE_REPORT_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                applicability_state_json_start_index = len(
                    self.log_keyword_table['LOG_MSFB_APPLICABILITY_STATE_JSON_INDICATOR'])
                applicability_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.applicability_state_json = json.loads(
                    cur_line[applicability_state_json_start_index: applicability_state_json_stop_index])
                if 'ApplicabilityState' not in self.applicability_state_json:
                    if 'ApplicabilityErrorOccurred' in self.applicability_state_json and 'ApplicabilityErrorCode' in self.applicability_state_json:
                        if self.applicability_state_json['ApplicabilityErrorOccurred']['NewValue'] == True:
                            if self.applicability_state_json['ApplicabilityErrorCode']['NewValue'] == -2146233079:
                                self.applicability_reason = "Network Issue when trying to Invoke WinGet command. Try removing Proxy/Firewall or switch to different network."
                                self.applicability = False
                else:
                    if self.applicability_state_json['ApplicabilityState']['NewValue'] == "Applicable":
                        self.applicability = True
                    else:
                        self.applicability = False
                    self.applicability_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_REPORTING_STATE_INDICATOR']):
                """
                Fix bug where pre detection time is empty.
                A user context Store app could be retrieved in poller session without logged on user. App will be shown as "NotComputed" in predetection and applicailablity. And app is not processed.
                <![LOG[[Win32App][ReportingManager] Sending status to company portal based on report: {"ApplicationId":"a6c180ce-e38d-425a-b44a-afeb56287ba0","ResultantAppState":-1,"ReportingImpact":{"DesiredState":1,"Classification":2,"ConflictReason":0,"ImpactingApps":[]},"WriteableToStorage":true,"CanGenerateComplianceState":true,"CanGenerateEnforcementState":false,"IsAppReportable":true,"IsAppAggregatable":true,"AvailableAppEnforcementFlag":0,"DesiredState":0,"DetectionState":3,"DetectionErrorOccurred":false,"DetectionErrorCode":null,"ApplicabilityState":1011,"ApplicabilityErrorOccurred":false,"ApplicabilityErrorCode":null,"EnforcementState":null,"EnforcementErrorCode":null,"TargetingMethod":0,"TargetingType":2,"InstallContext":1,"Intent":3,"InternalVersion":1,"DetectedIdentityVersion":null,"RemovalReason":null}]LOG]!><time="01:15:18.4595340" date="9-27-2024" component="AppWorkload" context="" type="1" thread="10" file="">
                "ApplicabilityState":1011 means user context app in system context poller session.
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_WIN32_REPORTING_STATE_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue
                reporting_state_json_start_index = len(
                    self.log_keyword_table['LOG_WIN32_REPORTING_STATE_START_INDICATOR'])
                reporting_state_json_stop_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.reporting_state_json = json.loads(
                    cur_line[reporting_state_json_start_index: reporting_state_json_stop_index])
                if self.reporting_state_json['ApplicabilityState'] == 1011:
                    self.pre_install_detection_time = cur_time
                    self.pre_install_detection = False
                    self.applicability = False
                    self.applicability_time = cur_time
                    self.applicability_reason = "User Context app will be processed after user logon"
            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_TRANSITION_DOWNLOAD_STATE_INDICATOR']):
                self.download_start_time = cur_time
                self.has_enforcement = True
            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_DOWNLOAD_SIZE_INDICATOR']):
                """
                System context MSFB download size indicator:
                """
                # Only Non 0 BytesRequired reflect actual download progress
                if not cur_line.startswith("<![LOG[[Package Manager] BytesRequired - 0BytesDownloaded "):
                    donwloaded_size_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MFSB_DOWNLOADED_SIZE_INDEX_INDICATOR']) + len(
                        self.log_keyword_table['LOG_MFSB_DOWNLOADED_SIZE_INDEX_INDICATOR'])
                    donwloaded_size_index_stop = cur_line.find(
                        self.log_keyword_table['LOG_MFSB_DOWNLOADED_SIZE_INDEX_END_INDICATOR'])
                    self.download_file_size = int(cur_line[donwloaded_size_index_start: donwloaded_size_index_stop])
                    if self.app_file_size <= 0:
                        self.app_file_size = 100
                    self.download_finish_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_USER_DOWNLOAD_PROGRESS_LINE_START_INDICATOR']):

                """
                User context MSFB download size indicator, no actual Bytes, only percentage.
                
                <![LOG[[WinGetMessageProcessor] Processing Progress for app = 3a272aef-2bfa-426d-9137-4d5402be15c6 and user = 528f5241-8074-44d8-bdc0-3cb237149dde - Operation Phase = Downloading - Downloaded bytes = 90 - Total bytes = 100.]LOG]!><time="21:21:30.4343553" date="10-29-2023" component="IntuneManagementExtension" context="" type="1" thread="22" file="">
                <![LOG[[WinGetMessageProcessor] Processing Progress for app = 3a272aef-2bfa-426d-9137-4d5402be15c6 and user = 528f5241-8074-44d8-bdc0-3cb237149dde - DebugInfo = State = Installing
                OperationType = Install
                BytesRequired = 0
                BytesDownloaded = 0
                DownloadProgress = 1
                Progress = 0.9
                ]LOG]!><time="21:21:30.4343553" date="10-29-2023" component="IntuneManagementExtension" context="" type="1" thread="22" file="">

                """
                if self.log_keyword_table['LOG_MSFB_USER_DOWNLOAD_SIZE_INDICATOR'] in cur_line:
                    donwloaded_size_index_start = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_USER_DOWNLOAD_SIZE_INDICATOR']) + len(
                        self.log_keyword_table['LOG_MSFB_USER_DOWNLOAD_SIZE_INDICATOR'])
                    donwloaded_size_index_stop = cur_line.find(
                        self.log_keyword_table['LOG_MSFB_USER_TOTAL_SIZE_INDICATOR'])

                    download_file_size = int(cur_line[donwloaded_size_index_start: donwloaded_size_index_stop])
                    if download_file_size == 0:
                        if self.download_start_time == "":
                            self.download_start_time = cur_time
                            self.has_enforcement = True
                    if self.download_file_size <= 100:
                        self.download_file_size = download_file_size
                        self.download_finish_time = cur_time
            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_TRANSITION_DOWNLOAD_FINISH_STATE_INDICATOR']):
                if self.download_file_size == -1 or self.app_file_size == -1:
                    self.download_file_size = 100
                    self.app_file_size = 100
                self.download_finish_time = cur_time
                self.download_success = True
                post_download = True

            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_TRANSITION_INSTALL_STATE_INDICATOR']):
                self.download_success = True
                self.install_start_time = cur_time
                self.installer_created_success = True
                post_download = True

            elif cur_line.startswith(self.log_keyword_table['LOG_MSFB_FINISH_EXECUTING_INDICATOR']):
                """
                MSFB UWP install stop indicator
                <![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Completed execution for app with id:
                """
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_MSFB_FINISH_EXECUTING_INDICATOR'])
                if cur_app_id != self.app_id:
                    continue

                self.installer_exit_success = True

                install_action_status_index_start = cur_line.find(
                    self.log_keyword_table['LOG_MSFB_INSTALL_ACTION_STATUS_INDICATOR']) + len(
                    self.log_keyword_table['LOG_MSFB_INSTALL_ACTION_STATUS_INDICATOR'])
                install_action_status_index_end = cur_line.find(
                    self.log_keyword_table['LOG_MSFB_INSTALL_ENFORCEMENT_INDICATOR']) - 3
                self.installation_result = cur_line[install_action_status_index_start:install_action_status_index_end]

                install_message_status_index_start = cur_line.find(
                    self.log_keyword_table['LOG_MSFB_INSTALL_EXCEPTION_INDICATOR']) + len(
                    self.log_keyword_table['LOG_MSFB_INSTALL_EXCEPTION_INDICATOR'])
                install_message_status_index_end = cur_line.find(
                    self.log_keyword_table['LOG_MSFB_INSTALL_EXECUTION_RESULT_INDICATOR']) - 3
                self.install_error_message = cur_line[
                                             install_message_status_index_start:install_message_status_index_end]

                post_install = True
                if self.install_finish_time == "":
                    self.install_finish_time = cur_time
                else:
                    continue

        if self.download_start_time != "":
            self.download_average_speed = self.convert_speedraw_to_string()

        # if self.install_context == 1:
        #     self.process_msfb_user_context_app_log()
        # elif self.install_context == 2:
        #     self.process_msfb_system_context_app_log()

    def generate_standalone_win32_app_meta_log_output(self, depth=0):
        """
        Include Win32
        :return:
        """
        interpreted_log_output = ""

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:',
                                                                                                         self.app_id),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:',
                                                                                                         self.app_name),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:',
                                                                                                         self.app_type),
            depth)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Not Assigned'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'App Intent:'
        right_string = ""
        if self.intent == 0:
            if self.subgraph_type == 1:
                right_string = "Filtered by Assignment filter"
            elif self.subgraph_type == 2:
                right_string = "Dependent app"
            elif self.subgraph_type == 3:
                right_string = "Superseded app"
        elif self.intent == 1:
            right_string = "Available Install"
        elif self.intent == 3:
            right_string = "Required Install"
        elif self.intent == 4:
            right_string = "Required Uninstall"

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'App Context:'
        right_string = ""
        if self.install_context == 1:
            right_string = "User"
        elif self.install_context == 2:
            right_string = "System"

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Has Dependent Apps:'
        right_string = 'No'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Has Superseded Apps:'
        right_string = 'No'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        # if not self.grs_expiry:
        #     log_line += 'Win32 app GRS is not expired. Win32 app will be reevaluated after last GRS time + 24 hours\n'

        return interpreted_log_output

    def generate_dependency_win32_app_meta_log_output(self, depth=0):
        interpreted_log_output = ""

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:',
                                                                                                         self.app_id),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:',
                                                                                                         self.app_name),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:',
                                                                                                         self.app_type),
            depth)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Dependent App'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

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

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'App Context:'
        right_string = ""
        if self.install_context == 1:
            right_string = "User"
        elif self.install_context == 2:
            right_string = "System"

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Has Dependent Apps:'
        right_string = 'Yes'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Has Superseded Apps:'
        right_string = 'No'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

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

            right_string += ('[' + child_app_name + ']')
            interpreted_log_output += \
                constructinterpretedlog.write_log_output_line_with_indent_depth(
                    constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output \
                        ("", right_string, logprocessinglibrary.CONST_META_DEPENDENT_APP_VALUE_INDEX), depth)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        return interpreted_log_output

    def generate_supercedence_win32_app_meta_log_output(self, depth=0):
        interpreted_log_output = ""

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:',
                                                                                                         self.app_id),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:',
                                                                                                         self.app_name),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:',
                                                                                                         self.app_type),
            depth)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Dependent App'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

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

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'App Context:'
        right_string = ""
        if self.install_context == 1:
            right_string = "User"
        elif self.install_context == 2:
            right_string = "System"

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Has Dependent Apps:'
        right_string = 'No'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Has Superseded Apps:'
        right_string = 'Yes'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)
        # List Dependent apps

        for each_supersedence_app_index in range(len(self.supersedence_apps_list)):
            each_supersedence_app = self.supersedence_apps_list[each_supersedence_app_index]
            child_app_id = each_supersedence_app['ChildId']
            child_auto_install = each_supersedence_app['Action']
            child_app_name = [match['Name'] for match in self.policy_json if match['Id'] == child_app_id].pop()
            right_string = str(each_supersedence_app_index + 1) + ". " + child_app_id + " [Auto Uninstall]: "

            if child_auto_install == 100:
                right_string += 'No '
            elif child_auto_install == 110:
                right_string += 'Yes '

            right_string += ('[' + child_app_name + ']')
            interpreted_log_output += \
                constructinterpretedlog.write_log_output_line_with_indent_depth(
                    constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output \
                        ("", right_string, logprocessinglibrary.CONST_META_DEPENDENT_APP_VALUE_INDEX), depth)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        return interpreted_log_output

    def generate_msfb_app_meta_log_output(self, depth=0):
        """
        Include MSFB
        :return:
        """
        interpreted_log_output = ""

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App ID:',
                                                                                                         self.app_id),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Name:',
                                                                                                         self.app_name),
            depth)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('App Type:',
                                                                                                         self.app_type),
            depth)
        left_string = 'Target Type:'
        right_string = ""
        if self.target_type == 0:
            right_string = 'Not Assigned'
        elif self.target_type == 1:
            right_string = 'User Group'
        elif self.target_type == 2:
            right_string = 'Device Group'
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'App Intent:'
        right_string = ""
        if self.intent == 0:
            if self.subgraph_type == 1:
                right_string = "Filtered by Assignment filter"
            elif self.subgraph_type == 2:
                right_string = "Dependent app"
            elif self.subgraph_type == 3:
                right_string = "Supercedence app"
        elif self.intent == 1:
            right_string = "Available Install"
        elif self.intent == 3:
            right_string = "Required Install"
        elif self.intent == 4:
            right_string = "Required Uninstall"

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'App Context:'
        right_string = ""
        if self.install_context == 1:
            right_string = "User"
        elif self.install_context == 2:
            right_string = "System"

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)
        # Adding feature for Betty to include store app package identifier
        left_string = 'Package Identifier:'
        right_string = self.package_identifier

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)
        left_string = 'Last Enforcement State:'
        right_string = self.last_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Current Enforcement State:'
        right_string = self.cur_enforcement_state
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Detected Version:'
        if self.msfb_detected_version != "":
            right_string = self.msfb_detected_version
        else:
            right_string = "None"
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'Installed Version:'
        if self.msfb_installed_version != "":
            right_string = self.msfb_installed_version
        else:
            right_string = "None"
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'GRS time:'
        right_string = (self.grs_time if self.grs_time != "" else 'No recorded GRS')
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        left_string = 'GRS expired:'
        right_string = str(self.grs_expiry)
        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string,
                                                                                                         right_string),
            depth)

        # if not self.grs_expiry:
        #     log_line += 'Win32 app GRS is not expired. Win32 app will be reevaluated after last GRS time + 24 hours\n'

        return interpreted_log_output

    def generate_msfb_post_download_log_output(self, depth=0):
        # This works for MSFB UWP
        interpreted_log_output = ""
        if not self.has_enforcement:
            if self.reason_need_output:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + " No action required for this app. " + self.no_enforcement_reason + '\n', depth)
            return interpreted_log_output

        if self.intent != 4:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_start_time + ' Start downloading app using WinGet.\n', )
        if self.download_success:
            if self.intent != 4:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' WinGet mode download completed.\n')
                computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_size_str + '\n', depth)

                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_speed_str + '\n', depth)
        else:
            if self.intent != 4:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' WinGet mode download FAILED! \n')
                computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
                if self.download_finish_time and self.download_file_size > -1:
                    interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                        self.download_finish_time + ' ' + computed_size_str + '\n', depth)
                    if self.app_file_size > 0:
                        total_size_str = "Total file size is: " + self.convert_file_size_to_readable_string(
                            self.app_file_size)
                        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                            self.download_finish_time + ' ' + total_size_str + '\n', depth)
                    interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                        self.download_finish_time + ' ' + computed_speed_str + '\n', depth)
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Installation Result: ' + result + '\n')
                return interpreted_log_output

        if self.install_context == 1:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_finish_time + ' Install Context: User\n')
        elif self.install_context == 2:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_finish_time + ' Install Context: System\n')
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_finish_time + ' Install Context: Unknown!\n')
        if self.installer_created_success:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Installer process created successfully. Installer time out is ' + self.installer_timeout_str + ' minutes.\n')
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Error creating installer process!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            if self.intent == 4:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installer_exit_success:
            if self.intent == 4:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Uninstallation is done.\n')
            else:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Installation is done.\n')
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Installer process timeout!\n')
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            if self.install_error_message != "":
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' Install Error message: ' + self.install_error_message + '\n')
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n')
            return interpreted_log_output
        if self.installation_result == "":
            self.installation_result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
        if self.intent == 4:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Uninstallation Result: ' + self.installation_result + '\n')
        else:
            # print(self.installation_result)
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Installation Result: ' + self.installation_result + '\n')

        if self.install_error_message != "":
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Install Error message: ' + self.install_error_message + '\n')

        if self.post_install_detection:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.post_install_detection_time +
                ' Detect app after processing: App is detected.\n'
                if self.post_install_detection_time != ""
                else self.install_finish_time +
                     ' Detect app after processing: App is detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Uninstallation Result: ' + result + '\n')
                return interpreted_log_output
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Installation Result: ' + result + '\n')
        else:
            if self.post_install_detection_time != "":
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.post_install_detection_time + ' Detect app after processing: App is NOT detected.\n')
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Uninstallation Result: ' + result + '\n')
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Installation Result: ' + result + '\n')
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
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + " No action required for this app. " + self.no_enforcement_reason + '\n', depth)
            return interpreted_log_output

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            self.download_start_time + ' Start downloading app using DO.\n', depth)
        if self.download_do_mode != "":
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_start_time + ' DO Download priority is: ' + self.download_do_mode + '\n', depth)
        if self.proxy_url != "":
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_start_time + ' Current Proxy is: ' + '\n' + self.proxy_url + '\n', depth)
        if self.download_url != "":
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_start_time + ' Current Download URL is: ' + '\n' + self.download_url + '\n', depth)
        if self.download_success:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_finish_time + ' DO mode download completed.\n', depth)
            computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_finish_time + ' ' + computed_size_str + '\n', depth)

            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.download_finish_time + ' ' + computed_speed_str + '\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' DO mode download FAILED! \n', depth)
            if self.download_finish_time and self.download_file_size > -1:
                computed_size_str, computed_speed_str = self.compute_download_size_and_speed()
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_size_str + '\n', depth)

                if self.app_file_size > 0:
                    total_size_str = "Total file size is: " + self.convert_file_size_to_readable_string(
                        self.app_file_size)
                    interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                        self.download_finish_time + ' ' + total_size_str + '\n', depth)

                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.download_finish_time + ' ' + computed_speed_str + '\n', depth)

            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.hash_validate_success:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.hash_validate_success_time + ' Hash validation pass.\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Hash validation FAILED! \n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.decryption_success:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.decryption_success_time + ' Decryption success.\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Decryption FAILED!\n',
                depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.unzipping_success:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.decryption_success_time + ' Unzipping success.\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Unzipping FAILED!\n',
                depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.skip_installation:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.post_download_detection_time + ' Aborting installation as app is detected.\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.install_context == 1:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Install Context: User\n', depth)
        elif self.install_context == 2:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Install Context: System\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Install Context: Unknown!\n', depth)
        if self.intent == 4:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Uninstall Command: ' + self.uninstall_command + '\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Install Command: ' + self.install_command + '\n', depth)
        if self.installer_created_success:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_start_time + ' Installer process created successfully. Installer time out is ' +
                self.installer_timeout_str + ' minutes.\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Error creating installer process!\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.installer_exit_success:
            if self.intent == 4:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Uninstallation is done. Exit code is: ' + str(
                        self.install_exit_code) + '\n', depth)
            else:
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.install_finish_time + ' Installation is done. Exit code is: ' + str(
                        self.install_exit_code) + '\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' Installer process timeout!\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output
        if self.intent == 4:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Uninstallation Result: ' + self.installation_result + '\n', depth)
        else:
            # print(self.installation_result)
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Installation Result: ' + self.installation_result + '\n', depth)

        '''
        RestartBehavior
        0: Return codes
        1: App install may force a device restart
        2: No specific action
        3: Intune will force a mandatory device restart
        '''
        if self.device_restart_behavior == 0:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Reboot Behavior: [Restart determined by return codes]\n', depth)
        elif self.device_restart_behavior == 1:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Reboot Behavior: [App install may force a device restart]\n', depth)
        elif self.device_restart_behavior == 2:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Reboot Status: [No specific action]\n', depth)
        elif self.device_restart_behavior == 3:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Reboot Behavior: [Intune will force a mandatory device restart]\n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Reboot Status: [Unknown]\n', depth)

        if self.post_install_detection:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.post_install_detection_time + ' Detect app after processing: App is detected.\n', depth) \
                if self.post_install_detection_time != "" \
                else constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.install_finish_time + ' Detect app after processing: App is detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Uninstallation Result: ' + result + '\n', depth)
                return interpreted_log_output
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Installation Result: ' + result + '\n', depth)
        else:
            if self.post_install_detection_time != "":
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.post_install_detection_time + ' Detect app after processing: App is NOT detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Uninstallation Result: ' + result + '\n', depth)
            else:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "FAIL"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.end_time + ' App Installation Result: ' + result + '\n', depth)
                return interpreted_log_output

        return interpreted_log_output

    def generate_win32app_pre_download_log_output(self, depth=0):
        # including predetection, grs, applicability logging.
        # This works for Win32 apps
        interpreted_log_output = ""

        """
        Filtered app does not have pre detection.
        """
        if self.filter_state == 1010:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + " App is not Applicable due to assignment filter.\n", depth)
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: Not Applicable\n', depth)
            self.has_enforcement = False
            return interpreted_log_output

        if self.pre_install_detection:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.pre_install_detection_time + ' Detect app before processing: App is detected.\n', depth)
            if self.intent != 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + ' App Installation Result: ' + result + '\n', depth)
                return interpreted_log_output
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.pre_install_detection_time + ' Detect app before processing: App is NOT detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + ' App Uninstallation Result: ' + result + '\n', depth)
                return interpreted_log_output

        if not self.grs_expiry:
            # Output detection results only
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.pre_install_detection_time + " Win32 app GRS is not expired. App will be detected only and NOT enforced.\n",
                depth)
            return interpreted_log_output

        if self.applicability:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.applicability_time + ' Applicability Check: Applicable \n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.applicability_time + ' Applicability Check: NOT Applicable \n', depth)
            if self.applicability_reason != "":
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.applicability_time + ' Not Applicable Reason: ' + self.applicability_reason + '\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "NOT Applicable"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.applicability_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output

        return interpreted_log_output

    def generate_msfb_pre_download_log_output(self, depth):
        # including predetection, grs, applicability logging.
        # This works for MSFB apps
        interpreted_log_output = ""

        """
        Filtered app does not have pre detection.
        """
        if self.filter_state == 1010:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + " App is not Applicable due to assignment filter.\n", depth)
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.end_time + ' App Installation Result: Not Applicable\n', depth)
            self.has_enforcement = False
            return interpreted_log_output

        if self.pre_install_detection:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.pre_install_detection_time + ' Detect app before processing: App is detected.\n', depth)
            if self.intent != 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + ' App Installation Result: ' + result + '\n', depth)
                return interpreted_log_output
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.pre_install_detection_time + ' Detect app before processing: App is NOT detected.\n', depth)
            if self.intent == 4:
                result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "SUCCEEDED"
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.pre_install_detection_time + ' App Uninstallation Result: ' + result + '\n', depth)
                return interpreted_log_output

        if not self.grs_expiry:
            # Output detection results only
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.pre_install_detection_time + " Win32 app GRS is not expired. App will be detected only and NOT enforced.\n",
                depth)
            return interpreted_log_output

        if self.applicability:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.applicability_time + ' Applicability Check: Applicable \n', depth)
        else:
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.applicability_time + ' Applicability Check: NOT Applicable \n', depth)
            if self.applicability_reason != "":
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    self.applicability_time + ' Not Applicable Reason: ' + self.applicability_reason + '\n', depth)
            # if self.no_enforcement_reason != "":
            #     interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
            #         self.applicability_time + ' No Enforcement Reason: ' + self.no_enforcement_reason + '\n', depth)
            result = self.cur_enforcement_state if self.cur_enforcement_state != "No enforcement state found" else "NOT Applicable"
            interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                self.applicability_time + ' App Installation Result: ' + result + '\n', depth)
            return interpreted_log_output

        return interpreted_log_output

    def generate_win32app_first_line_log_output(self, depth):
        interpreted_log_output = ""
        temp_log = ""
        temp_log += self.start_time + " Processing "
        if self.subgraph_type == 1:
            temp_log += "Standalone app: ["
        elif self.subgraph_type == 2:
            if self.dependent_apps_list is not None:
                if self.is_root_app:
                    temp_log += "Root "
                else:
                    temp_log += "Dependent "
                temp_log += "app with Dependency: ["
            else:
                temp_log += "Dependent standalone app: ["
        elif self.subgraph_type == 3:
            if self.is_root_app:
                temp_log += "Superceding app: ["
            else:
                temp_log += "Superceded app: ["
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
            if self.subgraph_type == 1:
                temp_log += "Filtered by Assignment filter"
            elif self.subgraph_type == 2:
                temp_log += "Dependent app"
            elif self.subgraph_type == 3:
                temp_log += "Superceded app"
        elif self.intent == 1:
            temp_log += "Available Install"
        elif self.intent == 3:
            temp_log += "Required Install"
        elif self.intent == 4:
            temp_log += "Required Uninstall"
        temp_log += '\n'

        interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(temp_log, depth)
        return interpreted_log_output

    def generate_standalone_win32app_log_output(self, depth=0):
        interpreted_log_output = ""
        interpreted_log_output += self.generate_win32app_first_line_log_output(depth)
        interpreted_log_output += self.generate_win32app_pre_download_log_output(depth)

        interpreted_log_output += self.generate_win32app_post_download_log_output(depth)

        return interpreted_log_output

    def generate_msfb_log_output(self, depth=0):
        interpreted_log_output = ""
        interpreted_log_output += self.generate_win32app_first_line_log_output(depth)
        interpreted_log_output += self.generate_msfb_pre_download_log_output(depth)

        interpreted_log_output += self.generate_msfb_post_download_log_output()

        return interpreted_log_output
