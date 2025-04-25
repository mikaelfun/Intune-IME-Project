"""
This is Class def for UserSession.
Each Application Poller may contain multiple UserSessions to process due to multiple licensed AAD users logged on
Create this class object for each UserSession.

Error Code range: 4000 - 4999

Class hierarchy:
- ImeInterpreter
    - EMSLifeCycle
        - ApplicationPoller
            -UserSession
                - SubGraph
                    - Win32App

"""
import json

import logprocessinglibrary
import subgraph
import constructinterpretedlog


class UserSession:
    def __init__(self, user_session_log, poller_thread_string):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.log_content = user_session_log
        if self.log_content[-1] == "":
            self.log_content.pop(-1)
        self.log_len = len(self.log_content)
        if self.log_len < 3 or len(self.log_content[0]) < 9:
            print("Error self.log_len < 3! Exit 4010")
            return
            # exit(3101)
        self.user_session_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])[:-4]
        self.thread_id = poller_thread_string
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])
        self.stop_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[-1])
        # self.app_processing_line_start, self.app_processing_line_stop = self.get_each_app_processing_lines()
        # self.number_of_apps_processed = len(self.app_processing_line_start)

        """
        <![LOG[[Win32App] ..................... Processing user session 0, userId: 00000000-0000-0000-0000-000000000000, userSID:  ..................... ]LOG]!><time="13:05:48.8261848" date="1-21-2025" component="AppWorkload" context="" type="2" thread="15" file="">
        <![LOG[[Win32App] ..................... Completed user session 0, userId: 00000000-0000-0000-0000-000000000000, userSID:  ..................... ]LOG]!><time="13:06:16.7819559" date="1-21-2025" component="AppWorkload" context="" type="2" thread="15" file="">

        <![LOG[[Win32App] ..................... Processing user session 2, userId: 76ab029d-1395-4203-a72b-a716d6117f91, userSID: S-1-12-1-1990918813-1107497877-380054439-2441023958 ..................... ]LOG]!><time="14:59:31.1487327" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">
        <![LOG[[Win32App] ..................... Completed user session 2, userId: 76ab029d-1395-4203-a72b-a716d6117f91, userSID: S-1-12-1-1990918813-1107497877-380054439-2441023958 ..................... ]LOG]!><time="15:03:17.5857511" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">

        """
        self.user_account = "No User"
        self.user_sid = ""
        self.user_session_apps_got = '0'
        self.comanagement_workload = "Unknown"
        self.has_expired_subgraph = False
        self.is_throttled = False
        self.app_type = ""
        self.esp_phase = "NotInEsp"
        self.sub_graph_list = []
        self.expired_sub_graph_list = []  # Expired subgraph list
        self.sub_graph_reevaluation_time_list = dict()
        self.user_session_reevaluation_check_in_time = ""
        self.get_policy_json = {}
        self.subgraph_num_expected = -1
        self.subgraph_num_actual = -1
        self.expired_subgraph_num_actual = 0
        self.index_list_subgraph_processing_start = []
        self.index_list_subgraph_processing_stop = []
        self.last_enforcement_json_dict = dict()

        self.init_user_session_meta_data()
        self.init_subgraph_list()


    def init_user_session_meta_data(self):
        for log_line_index in range(self.log_len):
            each_line = self.log_content[log_line_index]

            if logprocessinglibrary.locate_thread(each_line) != self.thread_id:
                # ignoring log not belonging to this poller thread. All these metadata are not related to UWP special case with new thread ID on installing.
                continue

            if each_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_START_INDICATOR']):
                user_id_start = each_line.find(", userId: ") + len(", userId: ")
                user_sid_start = each_line.find(", userSID: ") + len(", userSID: ")
                user_sid_end = each_line.find(" ..................... ]LOG]!>")

                self.user_sid = each_line[user_sid_start: user_sid_end]

            elif each_line.startswith(self.log_keyword_table['LOG_CO_MA_INDICATOR']):
                end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                if each_line[len(self.log_keyword_table['LOG_CO_MA_INDICATOR']):end_place] == "False":
                    self.comanagement_workload = "Intune"
                elif each_line[len(self.log_keyword_table['LOG_CO_MA_INDICATOR']):end_place] == "True":
                    self.comanagement_workload = "SCCM"
                else:
                    self.comanagement_workload = "Unknown"
            elif each_line.startswith(
                    self.log_keyword_table['LOG_ESP_INDICATOR']):  # get ESP phase
                if "in session]LOG]!" in each_line:
                    end_place = each_line.find("in session]LOG]!")
                else:
                    end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1
                self.esp_phase = each_line[len(self.log_keyword_table['LOG_ESP_INDICATOR']):end_place]
                '''
                <![LOG[[Win32App] The EspPhase: NotInEsp.]LOG]!
                <![LOG[[Win32App] The EspPhase: NotInEsp in session]LOG]!
                <![LOG[[Win32App] The EspPhase: DevicePreparation.]LOG]!
                <![LOG[[Win32App] The EspPhase: DeviceSetup.]LOG]!
                <![LOG[[Win32App] The EspPhase: AccountSetup.]LOG]!
                '''
            elif each_line.startswith(self.log_keyword_table['LOG_APP_MODE_INDICATOR']):
                if self.app_type:
                    print("Warning! Duplicate Request App Type marker in 1 user session! Exit 4100")
                start_place = len(self.log_keyword_table['LOG_APP_MODE_INDICATOR'])
                if each_line.find("available apps") > 0:
                    end_place = each_line.find(" apps only")
                    self.app_type = each_line[start_place:end_place]
                elif each_line.find("required apps") > 0:
                    end_place = each_line.find(" apps")
                    self.app_type = each_line[start_place:end_place]
                elif each_line.find("selected apps") > 0:
                    end_place = each_line.find(" apps")
                    self.app_type = each_line[start_place:end_place]
                else:
                    self.app_type = "Unknown"
                # print(self.app_type)
            elif each_line.startswith(
                    self.log_keyword_table['LOG_USER_INDICATOR']):  # get current user session
                if self.user_account == "No User":
                    # print("Warning! Duplicate User Account marker in 1 user session! Exit 4300")
                    end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                    self.user_account = each_line[len(self.log_keyword_table['LOG_USER_INDICATOR']):end_place]

            elif each_line.startswith(self.log_keyword_table['LOG_THROTTLED_INDICATOR']):
                self.is_throttled = True
            elif each_line.startswith(
                    self.log_keyword_table['LOG_POLLER_APPS_1_INDICATOR']) and self.log_keyword_table[
                'LOG_POLLER_APPS_2_INDICATOR'] in each_line:
                if self.user_session_apps_got != '0':
                    print("Warning! Duplicate User apps got marker in 1 user session! Exit 4400")
                end_place = each_line.find(self.log_keyword_table['LOG_POLLER_APPS_2_INDICATOR'])
                self.user_session_apps_got = each_line[len(self.log_keyword_table['LOG_POLLER_APPS_1_INDICATOR']):end_place]

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
            elif each_line.startswith(self.log_keyword_table['LOG_RE_EVAL_INDICATOR']):
                index_start = len(self.log_keyword_table['LOG_RE_EVAL_INDICATOR'])
                index_end = each_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1  # dropping .
                self.user_session_reevaluation_check_in_time = each_line[index_start:index_end]
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


    def init_subgraph_list(self):
        temp_index_list_subgraph_processing_start, temp_index_list_subgraph_processing_stop = [], []
        for log_line_index in range(self.log_len):
            cur_line = self.log_content[log_line_index]
            """
            Fix bug that will read other threads app processing.
            """
            if logprocessinglibrary.locate_thread(cur_line) != self.thread_id:
                continue
            if cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_START_INDICATOR']):
                temp_index_list_subgraph_processing_start.append(log_line_index)
            elif cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_END_INDICATOR']):
                temp_index_list_subgraph_processing_stop.append(log_line_index)
            elif cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_NOT_APPLICABLE_INDICATOR']):
                temp_index_list_subgraph_processing_stop.append(log_line_index)
            elif self.subgraph_num_expected == -1 and cur_line.startswith(
                    self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_1_INDICATOR']) \
                    and self.log_keyword_table[
                'LOG_V3_PROCESSOR_ALL_SUBGRAPH_2_INDICATOR'] in cur_line:  # get ESP phase
                subgraph_num_expected_index_start = len(
                    self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_1_INDICATOR'])
                subgraph_num_expected_index_end = cur_line.find(
                    self.log_keyword_table['LOG_V3_PROCESSOR_ALL_SUBGRAPH_2_INDICATOR'])
                subgraph_number = int(cur_line[subgraph_num_expected_index_start:subgraph_num_expected_index_end])
                self.subgraph_num_expected = subgraph_number
            elif cur_line.startswith(self.log_keyword_table['LOG_REPORTING_STATE_1_INDICATOR']) and \
                    (self.log_keyword_table['LOG_REPORTING_STATE_2_INDICATOR'] in cur_line or self.log_keyword_table[
                        'LOG_REPORTING_STATE_3_INDICATOR'] in cur_line):

                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table[
                    'LOG_REPORTING_STATE_1_INDICATOR'])
                reporting_state_start_index = cur_line.find('ReportingState: ') + len('ReportingState: ')
                reporting_state_end_index = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                reporting_state_json_string = cur_line[reporting_state_start_index:reporting_state_end_index]
                self.last_enforcement_json_dict[cur_app_id] = json.loads(reporting_state_json_string)

        # Support Subgraph ending pre-maturely
        if len(temp_index_list_subgraph_processing_start) == len(temp_index_list_subgraph_processing_stop) + 1:
            if temp_index_list_subgraph_processing_start[-1] > temp_index_list_subgraph_processing_stop[-1]:
                temp_index_list_subgraph_processing_stop.append(self.log_len - 1)

        self.index_list_subgraph_processing_start, self.index_list_subgraph_processing_stop = (
            logprocessinglibrary.align_index_lists(temp_index_list_subgraph_processing_start,
                                                   temp_index_list_subgraph_processing_stop))

        if len(self.index_list_subgraph_processing_start) == 0 or len(
                self.index_list_subgraph_processing_stop) == 0:
            # print("Warning No valid subgraph in this poller! Exit 4500. UserSession time stamp: " + self.start_time)
            return

        self.subgraph_num_actual = len(self.index_list_subgraph_processing_start)
        for each_subgraph_index in range(self.subgraph_num_actual):
            cur_subgraph_start = self.index_list_subgraph_processing_start[each_subgraph_index]
            cur_subgraph_stop = self.index_list_subgraph_processing_stop[each_subgraph_index]
            cur_subgraph_log = self.log_content[cur_subgraph_start: cur_subgraph_stop]
            cur_subgraph = subgraph.SubGraph(cur_subgraph_log, self.get_policy_json, self.last_enforcement_json_dict)

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
                self.has_expired_subgraph = True


    def generate_user_session_log_output(self, show_full_log):
        interpreted_log_output = ""

        """
        In Full log mode, show every app poller and every user session, no matter they are expired or not, available app check in with 0 apps or not.
        In simple log mode, only show app poller that has active user session and at least one expired subgraph.
        """
        if not show_full_log:
            if self.user_session_apps_got == '0' and self.app_type == 'available':
                # skipped because this is available app check in, not useful
                interpreted_log_output += "0 Apps got for available app check in. Skipping\n"
                return interpreted_log_output
            elif self.expired_subgraph_num_actual == 0:
                pass
                # interpreted_log_output += "All SubGraphs in this session are not Expired yet. Skipping\n"
                # return interpreted_log_output
        else:
            pass
            # if not self.sub_graph_list:
            #     interpreted_log_output += "0 SubGraphs inside this session. Skipping\n"
            #     return interpreted_log_output

        first_line = self.log_content[0]
        if first_line.startswith(
                self.log_keyword_table['LOG_USER_SESSION_PROCESS_START_INDICATOR']):
            interpreted_log_output += constructinterpretedlog.write_user_session_start_to_log_output(
                "User Session Starts",
                self.esp_phase, self.user_account, self.app_type,
                self.user_session_apps_got, self.user_session_time)
        else:
            interpreted_log_output += constructinterpretedlog.write_user_session_start_to_log_output(
                "User Session Missing Start",
                self.esp_phase, self.user_account, self.app_type,
                self.user_session_apps_got, self.user_session_time)

        interpreted_log_output += "\n"
        # Skip poller log if 0 expired subgraph number in this poller

        if not show_full_log:
            if self.expired_subgraph_num_actual <= 0:
                interpreted_log_output += "All SubGraphs in this session are not Expired yet. Skipping\n"
            else:
                interpreted_log_output += ("Processing " + str(self.expired_subgraph_num_actual) + " Expired Subgraph(s)\n")

            interpreted_log_output += '\n'
            for cur_subgraph_log_index in range(self.expired_subgraph_num_actual):
                cur_subgraph_log = self.expired_sub_graph_list[cur_subgraph_log_index]

                mid_string = ("Subgraph " + str(cur_subgraph_log_index + 1))
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_plus_to_log_output(mid_string)
                interpreted_log_output += constructinterpretedlog.write_empty_plus_to_log_output()
                interpreted_log_output += '\n'

                interpreted_log_output += cur_subgraph_log.generate_subgraph_log_output()
                interpreted_log_output += '\n'

            interpreted_log_output += "\n"
            last_line = self.log_content[-1]
            if last_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_STOP_INDICATOR']) or last_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_STOP_2_INDICATOR']):
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('User Session Stops')
                interpreted_log_output += constructinterpretedlog.write_empty_dash_to_log_output()
            else:
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('User Session Missing Stop')
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('log may be incomplete')
            interpreted_log_output += "\n"
        else:
            if self.subgraph_num_actual <= 0:
                interpreted_log_output += "0 SubGraphs inside this session.\n"
            elif self.subgraph_num_actual < self.subgraph_num_expected:
                interpreted_log_output += ("Expected " + str(self.subgraph_num_expected) + " Subgraph to read, found only "
                                           + str(self.subgraph_num_actual) + " from this log.\n\n")
            else:
                interpreted_log_output += ("Processing " + str(self.subgraph_num_expected) + " Subgraph(s)\n")

            interpreted_log_output += '\n'
            for cur_subgraph_log_index in range(self.subgraph_num_actual):
                cur_subgraph_log = self.sub_graph_list[cur_subgraph_log_index]

                mid_string = ("Subgraph " + str(cur_subgraph_log_index + 1))
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_plus_to_log_output(mid_string)
                mid_string = "Subgraph Expired" if cur_subgraph_log.reevaluation_expired else "Subgraph NOT Expired"
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_plus_to_log_output(mid_string)
                mid_string = "Subgraph Last Evaluation Time: " + cur_subgraph_log.reevaluation_time
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_plus_to_log_output(mid_string)
                interpreted_log_output += '\n'

                interpreted_log_output += cur_subgraph_log.generate_subgraph_log_output()
                interpreted_log_output += '\n'

            interpreted_log_output += "\n"
            last_line = self.log_content[-1]
            if last_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_STOP_INDICATOR']) or last_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_STOP_2_INDICATOR']):
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('User Session Stops')
                interpreted_log_output += constructinterpretedlog.write_empty_dash_to_log_output()
            else:
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('User Session Missing Stop')
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('log may be incomplete')
            interpreted_log_output += "\n"


        return interpreted_log_output