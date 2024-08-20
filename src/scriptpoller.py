import json

import logprocessinglibrary
import powershell


class ScriptPoller:
    def __init__(self, ps_poller_log, agent_executor_log_list):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.agent_executor_log_list = agent_executor_log_list
        self.log_content = list(ps_poller_log.split("\n"))
        if self.log_content[-1] == "":
            self.log_content.pop(-1)
        self.log_len = len(self.log_content)
        if self.log_len < 3 or len(self.log_content[0]) < 9:
            print("Warning PS.self.log_len < 3! Exit 3101")
            # return None
            # exit(3101)
        self.poller_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])[:-4]
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])
        self.stop_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[-1])
        self.esp_phase = ""
        self.user_session = ""
        self.poller_scripts_got = '-1'
        self.poller_scripts_after_filter = '-1'
        self.is_throttled = False
        self.get_policy_json = {}
        self.script_num_expected = -1
        self.script_num_actual = -1
        self.powershell_object_list = []

        self.init_ps_poller_meta_data()
        if not self.is_throttled and self.poller_scripts_after_filter > '0':
            self.initialize_ps_list()

    def init_ps_poller_meta_data(self):
        for log_line_index in range(self.log_len):
            each_line = self.log_content[log_line_index]
            if not self.user_session and each_line.startswith(self.log_keyword_table['LOG_USER_INDICATOR']):  # get current user session
                end_place = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.user_session = each_line[len(self.log_keyword_table['LOG_USER_INDICATOR']):end_place]
            elif self.poller_scripts_got == '-1' and each_line.startswith(
                    self.log_keyword_table['LOG_PS_POLLER_SCRIPT_1_INDICATOR']) and self.log_keyword_table['LOG_PS_POLLER_SCRIPT_2_INDICATOR'] in each_line:
                end_place = each_line.find(self.log_keyword_table['LOG_PS_POLLER_SCRIPT_2_INDICATOR'])
                self.poller_scripts_got = each_line[len(self.log_keyword_table['LOG_PS_POLLER_SCRIPT_1_INDICATOR']):end_place]
            # elif each_line.startswith(self.log_keyword_table['LOG_THROTTLED_INDICATOR']):
            #     self.is_throttled = True
            elif each_line.startswith(self.log_keyword_table['LOG_PS_POLICY_JSON_INDICATOR']):
                json_start_index = len(self.log_keyword_table['LOG_PS_POLICY_JSON_INDICATOR'])
                json_end_index = each_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                json_string = each_line[json_start_index:json_end_index]

                self.get_policy_json = json.loads(json_string)
            elif self.poller_scripts_after_filter == '-1' and each_line.startswith(self.log_keyword_table['LOG_PS_POLLER_SCRIPT_AFTER_FILTER_INDICATOR']):
                end_place = each_line.find(self.log_keyword_table['LOG_PS_POLLER_SCRIPT_2_INDICATOR'])
                self.poller_scripts_after_filter = each_line[
                                          len(self.log_keyword_table['LOG_PS_POLLER_SCRIPT_AFTER_FILTER_INDICATOR']):end_place]
                self.script_num_expected = int(self.poller_scripts_after_filter)

    def initialize_ps_list(self):
        """
        <![LOG[[PowerShell] Processing policy with id = d7c882ca-174a-40f4-b705-305b80883cd4 for user 00000000-0000-0000-0000-000000000000]LOG]!
        <![LOG[[PowerShell] User Id = 00000000-0000-0000-0000-000000000000, Policy id = d7c882ca-174a-40f4-b705-305b80883cd4, policy result = Success]LOG]!>
        """
        if self.script_num_expected <= 0:
            print("Info. Cannot find PowerShell processing line.")
            return None

        script_process_start_index_list = logprocessinglibrary.locate_line_startswith_keyword(self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_START_INDICATOR'])
        script_process_stop_index_list = logprocessinglibrary.locate_line_startswith_keyword(
            self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_STOP1_INDICATOR'])
        self.script_num_actual = len(script_process_start_index_list)
        if len(script_process_stop_index_list) != len(script_process_start_index_list):
            print("Warning! LOG_PS_SCRIPT_PROCESS_START_INDICATOR number and LOG_PS_SCRIPT_PROCESS_STOP1_INDICATOR number do not match!")

        for script_index in range(len(self.script_process_start_index_list)):
            cur_script_start_line_index = self.script_process_start_index_list[script_index]
            cur_script_stop_line_index = self.script_process_stop_index_list[script_index] + 1
            cur_script_agent_executor_log = self.get_cur_script_agent_executor_log(cur_script_start_line_index, cur_script_stop_line_index)
            cur_script = powershell.PowerShellObject(
                self.log_content[cur_script_start_line_index:cur_script_stop_line_index],
                self.get_policy_json, cur_script_agent_executor_log)

            self.powershell_object_list.append(cur_script)

    def get_cur_script_agent_executor_log(self, cur_script_start_line_index, cur_script_stop_line_index):
        return ""
