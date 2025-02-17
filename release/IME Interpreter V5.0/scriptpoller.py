import json

import logprocessinglibrary
import powershell
import constructinterpretedlog


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
                # print(each_line)
                # print("break")
                # fix a bug where this step may fail
                try:
                    self.get_policy_json = json.loads(json_string)
                except:
                    print(f"Failed to parse Script policy json string! Json sring is: ")
                    print(json_string)
                    continue
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

        script_process_start_index_list = logprocessinglibrary.locate_line_startswith_keyword(self.log_content, self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_START_INDICATOR'])
        script_process_stop_index_list = logprocessinglibrary.locate_line_startswith_keyword(self.log_content,
            self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_STOP1_INDICATOR'])
        self.script_num_actual = len(script_process_start_index_list)
        if len(script_process_stop_index_list) != len(script_process_start_index_list):
            print("Warning! LOG_PS_SCRIPT_PROCESS_START_INDICATOR number and LOG_PS_SCRIPT_PROCESS_STOP1_INDICATOR number do not match!")
            if len(script_process_start_index_list) == len(script_process_stop_index_list) + 1:
                if not script_process_stop_index_list:
                    script_process_stop_index_list.append(self.log_len-1)
                elif script_process_start_index_list[-1] > script_process_stop_index_list[-1]:
                    script_process_stop_index_list.append(self.log_len-1)
            elif len(script_process_start_index_list) + 1 == len(script_process_stop_index_list):
                if script_process_start_index_list[0] > script_process_stop_index_list[0]:
                    script_process_start_index_list.insert(0, 0)
            else:
                print("Warning! missing too many ps poller keywords.")

        while len(script_process_start_index_list) != 0 and len(script_process_stop_index_list) != 0:
            cur_script_start_line_index = script_process_start_index_list.pop(0)
            line_index_iter = cur_script_start_line_index + 1
            while line_index_iter < self.log_len:
                if line_index_iter in script_process_stop_index_list:
                    cur_script_stop_line_index = line_index_iter + 1
                    cur_script_stop_line_index = min(cur_script_stop_line_index, self.log_len - 1)
                    cur_script_id = logprocessinglibrary.find_app_id_with_starting_string(
                        self.log_content[cur_script_start_line_index],
                        self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_START_INDICATOR'])
                    cur_script_agent_executor_log_list = self.get_cur_script_agent_executor_log(cur_script_id,
                                                                                                cur_script_start_line_index,
                                                                                                cur_script_stop_line_index)
                    cur_script = powershell.PowerShellObject(cur_script_id,
                                                             self.log_content[
                                                             cur_script_start_line_index:cur_script_stop_line_index],
                                                             self.get_policy_json, cur_script_agent_executor_log_list)

                    self.powershell_object_list.append(cur_script)
                    script_process_stop_index_list.remove(line_index_iter)
                    break
                else:
                    line_index_iter = line_index_iter + 1

            if line_index_iter >= self.log_len:
                cur_script_stop_line_index = line_index_iter
                cur_script_stop_line_index = min(cur_script_stop_line_index, self.log_len - 1)
                cur_script_id = logprocessinglibrary.find_app_id_with_starting_string(
                    self.log_content[cur_script_start_line_index],
                    self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_START_INDICATOR'])
                cur_script_agent_executor_log_list = self.get_cur_script_agent_executor_log(cur_script_id,
                                                                                            cur_script_start_line_index,
                                                                                            cur_script_stop_line_index)
                cur_script = powershell.PowerShellObject(cur_script_id,
                                                         self.log_content[
                                                         cur_script_start_line_index:cur_script_stop_line_index],
                                                         self.get_policy_json, cur_script_agent_executor_log_list)

                self.powershell_object_list.append(cur_script)
                break

        if len(script_process_stop_index_list) != 0:
            # Dropping all
            print("Warning, dumping extra ps poller index stop: ")
            print(script_process_stop_index_list)
            script_process_stop_index_list.clear()

        if len(script_process_start_index_list) != 0:
            print("Warning, dumping extra ps poller index start: ")
            print(script_process_start_index_list)
            script_process_start_index_list.clear()

    def get_cur_script_agent_executor_log(self, cur_script_id, cur_script_start_line_index, cur_script_stop_line_index):
        cur_start_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[cur_script_start_line_index])
        cur_stop_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[cur_script_stop_line_index])
        for cur_line_index in range(len(self.agent_executor_log_list)):
            cur_log_lines = self.agent_executor_log_list[cur_line_index]
            cur_log_lines_as_list = list(cur_log_lines.split("\n"))
            for agent_ps_processing_log_each_line in cur_log_lines_as_list:
                if agent_ps_processing_log_each_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_ID_INDICATOR']):
                    start_index = len(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_ID_INDICATOR']) + logprocessinglibrary.CONST_USER_ID_LEN + 1
                    script_id_in_log = agent_ps_processing_log_each_line[start_index: start_index + logprocessinglibrary.CONST_APP_ID_LEN]
                    if script_id_in_log == cur_script_id:
                        cur_line_time = logprocessinglibrary.get_timestamp_by_line(agent_ps_processing_log_each_line)
                        if cur_start_time < cur_line_time < cur_stop_time:
                            return cur_log_lines_as_list
                        else:
                            break
                    else:
                        break
        return []

    def generate_powershell_poller_log_output(self):
        interpreted_log_output = ""
        if self.script_num_actual == 0 or self.poller_scripts_got == '0':
            # skipped because this is available app check in, not useful
            return interpreted_log_output

        first_line = self.log_content[0]
        if first_line.startswith(
                self.log_keyword_table['LOG_PS_POLLER_START']):
            interpreted_log_output += constructinterpretedlog.write_powershell_poller_start_to_log_output(
                "PowerShell Poller Starts",
                self.esp_phase, self.user_session,
                self.poller_scripts_got, self.poller_time)
        else:
            interpreted_log_output += constructinterpretedlog.write_powershell_poller_start_to_log_output(
                "PowerShell Poller Missing Start",
                self.esp_phase, self.user_session,
                self.poller_scripts_got, self.poller_time)

        interpreted_log_output += "\n"

        if self.script_num_actual == '0':
            interpreted_log_output += "No Scripts to be processed. Poller stops.\n"
            # return interpreted_log_output
        else:
            if self.script_num_actual < self.script_num_expected:
                interpreted_log_output += (
                            "Expected " + str(self.script_num_expected) + " PowerShell to read, found only "
                            + str(self.script_num_actual) + " from this log.\n\n")
            else:
                interpreted_log_output += ("Processing " + str(self.script_num_expected) + " PowerShell Script(s)\n")

            interpreted_log_output += '\n'
            for cur_script_log_index in range(self.script_num_actual):
                cur_script_log = self.powershell_object_list[cur_script_log_index]

                mid_string = ("Script " + str(cur_script_log_index + 1))
                interpreted_log_output += constructinterpretedlog.write_empty_plus_to_log_output()
                interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_plus_to_log_output(
                    mid_string)
                interpreted_log_output += constructinterpretedlog.write_empty_plus_to_log_output()
                interpreted_log_output += '\n'

                interpreted_log_output += cur_script_log.generate_powershell_log_output()
                interpreted_log_output += '\n'

        interpreted_log_output += "\n"
        last_line = self.log_content[-1]
        if last_line.startswith(self.log_keyword_table['LOG_PS_POLLER_STOP']):
            interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output(
                'PowerShell Poller Stops')
            interpreted_log_output += constructinterpretedlog.write_empty_dash_to_log_output()
        else:
            interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output(
                'PowerShell Poller Missing Stop')
            interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output(
                'log may be incomplete')

        return interpreted_log_output
