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

        self.get_poller_meta_data()
        if not self.is_throttled and self.poller_apps_got > '0':
            self.initialize_subgraph_list()

    def get_poller_meta_data(self):
        for log_line_index in range(self.log_len):
            each_line = self.log_content[log_line_index]
            if locate_thread(each_line) != self.thread_id:
                # ignoring log not belonging to this poller thread. All these metadata are not related to UWP special case with new thread ID on installing.
                continue

            if not self.esp_phase and each_line.startswith('<![LOG[[Win32App] The EspPhase:'):  # get ESP phase
                end_place = each_line.find(".]LOG]!")
                self.esp_phase = each_line[32:end_place]
                '''
                <![LOG[[Win32App] The EspPhase: NotInEsp.]LOG]!
                <![LOG[[Win32App] The EspPhase: DevicePreparation.]LOG]!
                <![LOG[[Win32App] The EspPhase: DeviceSetup.]LOG]!
                <![LOG[[Win32App] The EspPhase: AccountSetup.]LOG]!
                '''
            elif not self.user_session and each_line.startswith(
                    '<![LOG[After impersonation:'):  # get current user session
                end_place = each_line.find("]LOG]!")
                self.user_session = each_line[28:end_place]
            elif not self.comanagement_workload and each_line.startswith('<![LOG[Comgt app workload status '):
                end_place = each_line.find("]LOG]!")
                if each_line[33:end_place] == "False":
                    self.comanagement_workload = "Intune"
                elif each_line[33:end_place] == "True":
                    self.comanagement_workload = "SCCM"
                else:
                    self.comanagement_workload = "Unknown"
            elif not self.app_type and each_line.startswith('<![LOG[[Win32App] Requesting ') and (
                    'available apps only]' in each_line or 'required apps]' in each_line or 'for ESP]' in each_line):
                end_place = 29
                if each_line.find("available apps only]LOG]!") > 0:
                    end_place = each_line.find(" apps only]LOG]!")
                elif each_line.find("required apps]LOG]!") > 0:
                    end_place = each_line.find(" apps]LOG]!")
                elif each_line.find(" for ESP]") > 0:
                    end_place = each_line.find(" for ESP]")
                self.app_type = each_line[29:end_place]
            elif self.poller_apps_got == '0' and each_line.startswith(
                    '<![LOG[[Win32App] Got ') and 'Win32App(s) for user' in each_line:
                end_place = each_line.find(" Win32App(s) for user")
                self.poller_apps_got = each_line[22:end_place]
            elif each_line.startswith('<![LOG[Required app check in is throttled.'):
                self.is_throttled = True
            elif each_line.startswith('<![LOG[[Win32App][ReevaluationScheduleManager] Found previous reevaluation check-in time value: '):
                index_start = 96
                index_end = each_line.find('.]LOG]!>')
                self.poller_reevaluation_check_in_time = each_line[index_start:index_end]
            elif each_line.startswith('<![LOG[[Win32App][ReevaluationScheduleManager] Found previous subgraph reevaluation time value: '):
                index_start = 96
                index_end = each_line.find(' at key')
                sub_graph_reeval_time = each_line[index_start:index_end]
                index_start = index_end + 8
                index_end = each_line.find('.]LOG]')
                sub_graph_hash = each_line[index_start:index_end]
                # print(sub_graph_reeval_time)
                # print(sub_graph_hash)
                self.sub_graph_reevaluation_time_list[sub_graph_hash] = sub_graph_reeval_time
            elif each_line.startswith('<![LOG[Get policies = '):
                json_start_index = 22
                json_end_index = each_line.find(']LOG]!><time')
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
            if self.subgraph_num_expected == -1 and cur_line.startswith('<![LOG[[Win32App][V3Processor] Processing') \
                    and ' subgraphs.]LOG]!' in cur_line:  # get ESP phase
                subgraph_num_expected_index_start = 42
                subgraph_num_expected_index_end = cur_line.find(' subgraphs.]')
                subgraph_number = int(cur_line[subgraph_num_expected_index_start:subgraph_num_expected_index_end])
                self.subgraph_num_expected = subgraph_number
            elif cur_line.startswith('<![LOG[[Win32App][ReportingManager] App with id: ') and \
                    ('and prior AppAuthority: V3 has been loaded and reporting state initialized' in cur_line
                     or
                     'could not be loaded from store. Reporting state initialized with initial values. ReportingState: '
                     in cur_line):

                app_id_index_start = cur_line.find('App with id: ') + 13
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                reporting_state_start_index = cur_line.find('ReportingState: ') + 16
                reporting_state_end_index = cur_line.find(']LOG]!')
                reporting_state_json_string = cur_line[reporting_state_start_index:reporting_state_end_index]
                self.last_enforcement_json_dict[cur_app_id] = json.loads(reporting_state_json_string)
            elif cur_line.startswith('<![LOG[[Win32App][V3Processor] Processing subgraph with app ids: '):
                self.index_list_subgraph_processing_start.append(log_line_index)
            elif cur_line.startswith('<![LOG[[Win32App][V3Processor] Done processing subgraph.'):
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
                while len(self.index_list_subgraph_processing_start) != len(self.index_list_subgraph_processing_stop):
                    self.index_list_subgraph_processing_start.pop(-1)
            else:
                while len(self.index_list_subgraph_processing_stop) != len(self.index_list_subgraph_processing_start):
                    self.index_list_subgraph_processing_stop.pop(-1)

            # exit(3103)

        self.subgraph_num_actual = len(self.index_list_subgraph_processing_start)

        for subgraph_index in range(len(self.index_list_subgraph_processing_start)):
            cur_subgraph_start_line_index = self.index_list_subgraph_processing_start[subgraph_index]
            cur_subgraph_stop_line_index = self.index_list_subgraph_processing_stop[subgraph_index]
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
                '<![LOG[[Win32App] ----------------------------------------------------- application poller starts.'):
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
        if last_line.startswith(
                '<![LOG[[Win32App] ----------------------------------------------------- application poller stopped.'):
            interpreted_log_output += write_string_in_middle_with_dash_to_log_output('Application Poller Stops')
            interpreted_log_output += write_empty_dash_to_log_output()
        else:
            interpreted_log_output += write_string_in_middle_with_dash_to_log_output('Application Poller Missing Stop')
            interpreted_log_output += write_string_in_middle_with_dash_to_log_output('log may be incomplete')

        return interpreted_log_output
