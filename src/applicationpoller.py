"""
This is Class def for Application Poller.
Each EMS lifecycle may contain multiple Application Poller sessions due to scheduled check-ins
Create this class object for each Application Poller.

Error Code range: 3000 - 3999

Class hierarchy:
- ImeInterpreter
    - EMSLifeCycle
        - ApplicationPoller
            - SubGraph
                - Win32App

"""

from logprocessinglibrary import *
import datetime
import json
from constructinterpretedlog import *
from subgraph import *


class ApplicationPoller:
    def __init__(self, poller_log, poller_thread_string):
        self.log_keyword_table = init_keyword_table()
        self.log_content = list(poller_log.split("\n"))
        if self.log_content[-1] == "":
            self.log_content.pop(-1)
        self.log_len = len(self.log_content)
        if self.log_len < 3 or len(self.log_content[0]) < 9:
            print("Error self.log_len < 3! Exit 3101")
            return None
            # exit(3101)
        self.poller_time = get_timestamp_by_line(self.log_content[0])
        self.thread_id = poller_thread_string
        self.start_time = get_timestamp_by_line(self.log_content[0])
        self.stop_time = get_timestamp_by_line(self.log_content[-1])
        # self.app_processing_line_start, self.app_processing_line_stop = self.get_each_app_processing_lines()
        # self.number_of_apps_processed = len(self.app_processing_line_start)
        self.esp_phase = ""
        self.user_session = ""
        self.poller_apps_got = '0'
        self.comanagement_workload = ""
        self.app_type = ""
        self.is_throttled = False
        self.sub_graph_list = []
        self.expired_sub_graph_list = []  # Expired subgraph list
        self.sub_graph_reevaluation_time_list = dict()
        self.poller_reevaluation_check_in_time = ""
        self.get_policy_json = {}
        self.subgraph_num_expected = -1
        self.subgraph_num_actual = -1
        self.expired_subgraph_num_actual = 0
        self.index_list_subgraph_processing_start = []
        self.index_list_subgraph_processing_stop = []
        self.last_enforcement_json_dict = dict()

        self.init_app_poller_meta_data()
        if not self.is_throttled and self.poller_apps_got > '0':
            self.initialize_subgraph_list()

    def init_app_poller_meta_data(self):
        for log_line_index in range(self.log_len):
            each_line = self.log_content[log_line_index]
            if locate_thread(each_line) != self.thread_id:
                # ignoring log not belonging to this poller thread. All these metadata are not related to UWP special case with new thread ID on installing.
                continue

            if not self.esp_phase and each_line.startswith(self.log_keyword_table['LOG_ESP_INDICATOR']):  # get ESP phase
                end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1
                self.esp_phase = each_line[len(self.log_keyword_table['LOG_ESP_INDICATOR']):end_place]
                '''
                <![LOG[[Win32App] The EspPhase: NotInEsp.]LOG]!
                <![LOG[[Win32App] The EspPhase: DevicePreparation.]LOG]!
                <![LOG[[Win32App] The EspPhase: DeviceSetup.]LOG]!
                <![LOG[[Win32App] The EspPhase: AccountSetup.]LOG]!
                '''
            elif not self.user_session and each_line.startswith(self.log_keyword_table['LOG_USER_INDICATOR']):  # get current user session
                end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.user_session = each_line[len(self.log_keyword_table['LOG_USER_INDICATOR']):end_place]
            elif not self.comanagement_workload and each_line.startswith(self.log_keyword_table['LOG_CO_MA_INDICATOR']):
                end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                if each_line[len(self.log_keyword_table['LOG_CO_MA_INDICATOR']):end_place] == "False":
                    self.comanagement_workload = "Intune"
                elif each_line[len(self.log_keyword_table['LOG_CO_MA_INDICATOR']):end_place] == "True":
                    self.comanagement_workload = "SCCM"
                else:
                    self.comanagement_workload = "Unknown"
            elif not self.app_type and each_line.startswith(self.log_keyword_table['LOG_APP_MODE_INDICATOR']) and (
                    'available apps only]' in each_line or 'required apps]' in each_line or 'for ESP]' in each_line):
                start_place = len(self.log_keyword_table['LOG_APP_MODE_INDICATOR'])
                if each_line.find("available apps only]LOG]!") > 0:
                    end_place = each_line.find(" apps only]LOG]!")
                elif each_line.find("required apps]LOG]!") > 0:
                    end_place = each_line.find(" apps]LOG]!")
                elif each_line.find(" for ESP]") > 0:
                    end_place = each_line.find(" for ESP]")
                self.app_type = each_line[start_place:end_place]
            elif self.poller_apps_got == '0' and each_line.startswith(
                    self.log_keyword_table['LOG_POLLER_APPS_1_INDICATOR']) and self.log_keyword_table['LOG_POLLER_APPS_2_INDICATOR'] in each_line:
                end_place = each_line.find(self.log_keyword_table['LOG_POLLER_APPS_2_INDICATOR'])
                self.poller_apps_got = each_line[len(self.log_keyword_table['LOG_POLLER_APPS_1_INDICATOR']):end_place]
            elif each_line.startswith(self.log_keyword_table['LOG_THROTTLED_INDICATOR']):
                self.is_throttled = True
            elif each_line.startswith(self.log_keyword_table['LOG_RE_EVAL_INDICATOR']):

                index_start = len(self.log_keyword_table['LOG_RE_EVAL_INDICATOR'])
                index_end = each_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1  # dropping .
                self.poller_reevaluation_check_in_time = each_line[index_start:index_end]
            elif each_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_RE_EVAL_INDICATOR']):
                index_start = len(self.log_keyword_table['LOG_SUBGRAPH_RE_EVAL_INDICATOR'])
                log_subgraph_hash_indicator = ' at key '
                index_end = each_line.find(log_subgraph_hash_indicator)
                sub_graph_reeval_time = each_line[index_start:index_end]
                index_start = index_end + len(log_subgraph_hash_indicator)
                index_end = each_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1  # dropping .
                sub_graph_hash = each_line[index_start:index_end]
                # print(sub_graph_reeval_time)
                # print(sub_graph_hash)
                self.sub_graph_reevaluation_time_list[sub_graph_hash] = sub_graph_reeval_time
            elif each_line.startswith(self.log_keyword_table['LOG_POLICY_JSON_INDICATOR']):
                json_start_index = len(self.log_keyword_table['LOG_POLICY_JSON_INDICATOR'])
                json_end_index = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                json_string = each_line[json_start_index:json_end_index]

                self.get_policy_json = json.loads(json_string)
                """
                There is one bug that in get policy json, "InstallContext":1 always.
                So in order to get correct InstallContext for each app, find install context in <![LOG[[Win32App][ReportingManager] App with id: 
                <![LOG[[Win32App][ReportingManager] App with id: 9c393ca7-92fc-4e9e-94d0-f8e303734f7b and prior AppAuthority: V3 has been loaded and reporting state initialized. ReportingState: { 
                <![LOG[[Win32App][ReportingManager] App with id: 0557caed-3f50-499f-a39d-5b1179f78922 and prior AppAuthority: V2 could not be loaded from store. Reporting state initialized with initial values. ReportingState: 
                """
                # print(self.get_policy_json)

    def initialize_subgraph_list(self):
        """
        searching keyword 'subgraphs.]LOG]!':
        <![LOG[[Win32App][V3Processor] Processing 1 subgraphs.]LOG]!>
        <![LOG[[Win32App][V3Processor] Done processing 1 subgraphs.]LOG]!

        searching keyword '<![LOG[[Win32App][V3Processor] Processing':
        <![LOG[[Win32App][V3Processor] Processing 1 subgraphs.]LOG]!>
        <![LOG[[Win32App][V3Processor] Processing subgraph with app ids:

        so the common element should be the target line we are looking at. and it should only contain 1 element.
        """

        for log_line_index in range(self.log_len):
            cur_line = self.log_content[log_line_index]
            """
            Fix bug that will read other threads app processing.
            """
            if locate_thread(cur_line) != self.thread_id:
                continue
            if self.subgraph_num_expected == -1 and cur_line.startswith(self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_1_INDICATOR']) \
                    and self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_2_INDICATOR'] in cur_line:  # get ESP phase
                subgraph_num_expected_index_start = len(self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_1_INDICATOR'])
                subgraph_num_expected_index_end = cur_line.find(self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_2_INDICATOR'])
                subgraph_number = int(cur_line[subgraph_num_expected_index_start:subgraph_num_expected_index_end])
                self.subgraph_num_expected = subgraph_number
            elif cur_line.startswith(self.log_keyword_table['LOG_REPORTING_STATE_1_INDICATOR']) and \
                    (self.log_keyword_table['LOG_REPORTING_STATE_2_INDICATOR'] in cur_line or self.log_keyword_table['LOG_REPORTING_STATE_3_INDICATOR'] in cur_line):

                cur_app_id = find_app_id_with_starting_string(cur_line, self.log_keyword_table['LOG_REPORTING_STATE_1_INDICATOR'])
                reporting_state_start_index = cur_line.find('ReportingState: ') + len('ReportingState: ')
                reporting_state_end_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                reporting_state_json_string = cur_line[reporting_state_start_index:reporting_state_end_index]
                self.last_enforcement_json_dict[cur_app_id] = json.loads(reporting_state_json_string)
            elif cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_START_INDICATOR']):
                """
                Supercedence subgraph ending is ambiguous.
                
                <![LOG[[Win32App][ActionProcessor] Calculating desired states for all subgraphs. The computed desired states may be overridden as resolution continues.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Updating desired states for subgraph with id: c5b3ad1e-19ae-4b6e-90b5-1e9e329fb451.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Found: 0 apps with intent to uninstall before enforcing installs: [].]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Found: 1 apps with intent to install: [fc7d1ee3-2778-4312-8496-7d5d2e13695b].]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Found: 0 apps with intent to uninstall after enforcing installs: [].]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Evaluating install enforcement actions for app with id: fc7d1ee3-2778-4312-8496-7d5d2e13695b.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] No action required for app with id: fc7d1ee3-2778-4312-8496-7d5d2e13695b.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Updating desired states for subgraph with id: 30a3c1f4-d552-47a5-ac5f-f882c460a1f9.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Found: 0 apps with intent to uninstall before enforcing installs: [].]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Found: 1 apps with intent to install: [13a7b5f5-9512-42d1-a8d4-e486f1dfe614].]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Found: 0 apps with intent to uninstall after enforcing installs: [].]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] Evaluating install enforcement actions for app with id: 13a7b5f5-9512-42d1-a8d4-e486f1dfe614.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ActionProcessor] No action required for app with id: 13a7b5f5-9512-42d1-a8d4-e486f1dfe614.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ReportingManager] Sending status to company portal based on report: {"ApplicationId":"13a7b5f5-9512-42d1-a8d4-e486f1dfe614","ResultantAppState":1,"ReportingImpact":{"DesiredState":3,"Classification":2,"ConflictReason":0,"ImpactingApps":[{"AppId":"fc7d1ee3-2778-4312-8496-7d5d2e13695b","RelationshipType":2,"RelativeType":1,"DesiredState":3}]},"WriteableToStorage":true,"CanGenerateComplianceState":true,"CanGenerateEnforcementState":true,"IsAppReportable":true,"IsAppAggregatable":true,"AvailableAppEnforcementFlag":0,"DesiredState":2,"DetectionState":1,"DetectionErrorOccurred":false,"DetectionErrorCode":null,"ApplicabilityState":0,"ApplicabilityErrorOccurred":false,"ApplicabilityErrorCode":null,"EnforcementState":1000,"EnforcementErrorCode":0,"TargetingMethod":0,"TargetingType":2,"InstallContext":2,"Intent":3,"InternalVersion":1,"DetectedIdentityVersion":null,"RemovalReason":null}]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][StatusServiceReportsStore] Saved AppInstallStatusReport for user 536e85c2-2d7a-4b05-968c-1345a861286e for app 13a7b5f5-9512-42d1-a8d4-e486f1dfe614 in the StatusServiceReports registry.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[StatusService] Sending update from StatusServicePublisher.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[StatusService] Received AppInstallStatusUpdate to send via Callback.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[StatusService] Sending an update to user 536e85c2-2d7a-4b05-968c-1345a861286e via callback for app: 13a7b5f5-9512-42d1-a8d4-e486f1dfe614. Applicability: Applicable, Status: Installed, ErrorCode: null]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][ReportingManager] Not sending status update for user with id: 536e85c2-2d7a-4b05-968c-1345a861286e and app: fc7d1ee3-2778-4312-8496-7d5d2e13695b because the app does not have available, required, or uninstall intent.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][GRSManager] Saving GRS values to storage.]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                <![LOG[[Win32App][V3Processor] Processing subgraph with app ids: 30664d04-0476-4cbe-b3a8-7dbeac0cb5d4, 513fd40d-27eb-41da-b221-b9a1b19ebfe3]LOG]!><time="08:26:58.0888164" date="5-23-2023" component="IntuneManagementExtension" context="" type="1" thread="16" file="">
                
                Manual add subgraph ending if does not find ending keywords Done processing subgraph
                """
                if self.index_list_subgraph_processing_stop and self.index_list_subgraph_processing_stop[-1] < log_line_index - 1:
                    self.index_list_subgraph_processing_stop.append(log_line_index - 1)
                self.index_list_subgraph_processing_start.append(log_line_index)

            elif cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_END_INDICATOR']):
                if self.index_list_subgraph_processing_stop and self.index_list_subgraph_processing_stop[-1] == log_line_index:
                    pass
                else:
                    self.index_list_subgraph_processing_stop.append(log_line_index)
            elif cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_NOT_APPLICABLE_INDICATOR']):
                self.index_list_subgraph_processing_stop.append(log_line_index)

        if self.subgraph_num_expected <= 0:
            print("Info. Cannot find V3Processor subgraph number line.")
            return None

        if len(self.index_list_subgraph_processing_start) != len(self.index_list_subgraph_processing_stop):
            # print("Error! Subgraph processing beginning and stopping lines do not match! Exit 3103")
            # incomplete log, process as much as possible.
            # print(self.log_content)
            # print(index_list_subgraph_processing_start)
            # print(index_list_subgraph_processing_stop)
            # print(self.subgraph_num_expected)
            # print(self.subgraph_num_actual)
            if len(self.index_list_subgraph_processing_start) > len(self.index_list_subgraph_processing_stop):
                if len(self.index_list_subgraph_processing_start) == len(self.index_list_subgraph_processing_stop) + 1:
                    self.index_list_subgraph_processing_stop.append(self.log_len - 1)
                # while len(self.index_list_subgraph_processing_start) != len(self.index_list_subgraph_processing_stop):
                #     self.index_list_subgraph_processing_start.pop(-1)
            else:
                while len(self.index_list_subgraph_processing_stop) != len(self.index_list_subgraph_processing_start):
                    self.index_list_subgraph_processing_stop.pop(-1)

            # exit(3103)

        self.subgraph_num_actual = len(self.index_list_subgraph_processing_start)

        for subgraph_index in range(len(self.index_list_subgraph_processing_start)):
            cur_subgraph_start_line_index = self.index_list_subgraph_processing_start[subgraph_index]
            cur_subgraph_stop_line_index = self.index_list_subgraph_processing_stop[subgraph_index] + 1
            cur_subgraph = SubGraph(self.log_content[cur_subgraph_start_line_index:cur_subgraph_stop_line_index],
                                    self.get_policy_json, self.last_enforcement_json_dict)

            # Overwrite from poller to Subgraph object
            if cur_subgraph.hash_key in self.sub_graph_reevaluation_time_list.keys():
                cur_subgraph.reevaluation_time = self.sub_graph_reevaluation_time_list[cur_subgraph.hash_key]
            else:
                # Overwrite from object initialized value to poller subgraph reeval time stored.
                self.sub_graph_reevaluation_time_list[cur_subgraph.hash_key] = cur_subgraph.reevaluation_time
            self.sub_graph_list.append(cur_subgraph)
            if cur_subgraph.reevaluation_expired:
                self.expired_subgraph_num_actual = self.expired_subgraph_num_actual + 1
                self.expired_sub_graph_list.append(cur_subgraph)

    def generate_application_poller_log_output(self, show_not_expired_subgraph):
        interpreted_log_output = ""
        if self.poller_apps_got == '0' and self.app_type == 'available':
            # skipped because this is available app check in, not useful
            return interpreted_log_output

        # Skip poller log if 0 expired subgraph number in this poller
        if not show_not_expired_subgraph and self.expired_subgraph_num_actual == 0:
            return interpreted_log_output

        first_line = self.log_content[0]
        if first_line.startswith(
                self.log_keyword_table['LOG_APP_POLLER_START_STRING']):
            interpreted_log_output += write_application_poller_start_to_log_output(
                "Application Poller Starts",
                self.esp_phase, self.user_session,
                self.comanagement_workload, self.app_type,
                self.poller_apps_got, self.poller_time)
        else:
            interpreted_log_output += write_application_poller_start_to_log_output(
                "Application Poller Missing Start",
                self.esp_phase, self.user_session,
                self.comanagement_workload, self.app_type,
                self.poller_apps_got, self.poller_time)

        interpreted_log_output += "\n"

        if self.is_throttled:
            interpreted_log_output += 'App Check in is throttled due to too many requests. Please check in again in the next hour.\n\n'
            # return interpreted_log_output
        else:
            if self.poller_apps_got == '0':
                interpreted_log_output += "No Apps to be processed. Poller stops.\n"
                # return interpreted_log_output
            else:
                if show_not_expired_subgraph:
                    if self.subgraph_num_actual < self.subgraph_num_expected:
                        interpreted_log_output += ("Expected " + str(self.subgraph_num_expected) + " Subgraph to read, found only "
                                                   + str(self.subgraph_num_actual) + " from this log.\n\n")
                    else:
                        interpreted_log_output += ("Processing " + str(self.subgraph_num_expected) + " Subgraph(s)\n")

                    interpreted_log_output += '\n'
                    for cur_subgraph_log_index in range(self.subgraph_num_actual):
                        cur_subgraph_log = self.sub_graph_list[cur_subgraph_log_index]

                        mid_string = ("Subgraph " + str(cur_subgraph_log_index + 1))
                        interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                        mid_string = "Subgraph Expired" if cur_subgraph_log.reevaluation_expired else "Subgraph NOT Expired"
                        interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                        mid_string = "Subgraph Last Evaluation Time: " + cur_subgraph_log.reevaluation_time
                        interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                        interpreted_log_output += '\n'

                        interpreted_log_output += cur_subgraph_log.generate_subgraph_log_output()
                        interpreted_log_output += '\n'
                else:
                    if self.expired_subgraph_num_actual == 0:
                        interpreted_log_output += "All Subgraphs are NOT expired. Poller stops.\n"
                    else:
                        interpreted_log_output += ("Processing " + str(self.expired_subgraph_num_actual) + " expired Subgraph(s)\n")

                        for cur_subgraph_log_index in range(self.expired_subgraph_num_actual):
                            cur_subgraph_log = self.expired_sub_graph_list[cur_subgraph_log_index]
                            if show_not_expired_subgraph:
                                mid_string = ("Subgraph " + str(cur_subgraph_log_index + 1))
                                interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                                mid_string = "Subgraph Expired" if cur_subgraph_log.reevaluation_expired else "Subgraph NOT Expired"
                                interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                                mid_string = "Subgraph Last Evaluation Time: " + cur_subgraph_log.reevaluation_time
                                interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                            else:
                                # interpreted_log_output += write_empty_plus_to_log_output()
                                mid_string = ("Subgraph " + str(cur_subgraph_log_index + 1))
                                interpreted_log_output += write_string_in_middle_with_plus_to_log_output(mid_string)
                                interpreted_log_output += write_empty_plus_to_log_output()

                            interpreted_log_output += '\n'

                            interpreted_log_output += cur_subgraph_log.generate_subgraph_log_output()
                            interpreted_log_output += '\n'

        interpreted_log_output += "\n"
        last_line = self.log_content[-1]
        if last_line.startswith(self.log_keyword_table['LOG_APP_POLLER_STOP_STRING']):
            interpreted_log_output += write_string_in_middle_with_dash_to_log_output('Application Poller Stops')
            interpreted_log_output += write_empty_dash_to_log_output()
        else:
            interpreted_log_output += write_string_in_middle_with_dash_to_log_output('Application Poller Missing Stop')
            interpreted_log_output += write_string_in_middle_with_dash_to_log_output('log may be incomplete')

        return interpreted_log_output
