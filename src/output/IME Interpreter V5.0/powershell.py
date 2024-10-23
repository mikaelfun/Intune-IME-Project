import json

import constructinterpretedlog
import logprocessinglibrary


class PowerShellObject:
    def __init__(self, script_id, ime_log_list, policy_json, agent_executor_log_list):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.ime_log_list = ime_log_list
        self.script_id = script_id
        self.policy_json = policy_json
        self.current_script_json = {}
        self.agent_executor_log_list = agent_executor_log_list
        self.ime_log_len = len(self.ime_log_list)
        self.agent_executor_log_len = len(self.agent_executor_log_list)
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.ime_log_list[0])
        self.stop_time = logprocessinglibrary.get_timestamp_by_line(self.ime_log_list[-1])

        self.script_exec_user_id = ""
        self.context = -1
        self.bit32or64 = -1
        self.exit_code = "Unknown"
        self.sig_check = False
        self.error_message = ""
        self.output = ""
        self.script_body = ""
        self.script_start_time = ""
        self.script_stop_time = ""
        self.execution_result = "Unknown"

        self.interpret_script_log()
        # print("here")

    def interpret_script_log(self):
        for each_dic in self.policy_json:
            if each_dic['PolicyId'] == self.script_id:
                self.current_script_json = each_dic
                break
        if not self.current_script_json:
            print("Error! Unable to find powershell script ID in policy json!")
            return None
        self.context = self.current_script_json['ExecutionContext']
        # ? TODO
        if self.context == 1:
            self.context = "User"
        elif self.context == 0:
            self.context = "System"
        else:
            self.context = "Unknown"
        self.bit32or64 = self.current_script_json['RunningMode']
        self.script_body = self.current_script_json['PolicyBody']
        self.sig_check = self.current_script_json['EnforceSignatureCheck']

        for line_index in range(self.ime_log_len):
            cur_ime_line = self.ime_log_list[line_index]
            if cur_ime_line.startswith(self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_STOP1_INDICATOR']):
                self.script_exec_user_id = logprocessinglibrary.find_app_id_with_starting_string(cur_ime_line, self.log_keyword_table['LOG_PS_SCRIPT_PROCESS_STOP1_INDICATOR'])
                if self.log_keyword_table['LOG_PS_SCRIPT_RESULT2_INDICATOR'] in cur_ime_line:
                    start_index = cur_ime_line.find(self.log_keyword_table['LOG_PS_SCRIPT_RESULT2_INDICATOR']) + len(self.log_keyword_table['LOG_PS_SCRIPT_RESULT2_INDICATOR'])
                    end_index = cur_ime_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                    self.execution_result = cur_ime_line[start_index:end_index]
        line_index = 0
        while line_index < self.agent_executor_log_len:
            cur_ae_log_line = self.agent_executor_log_list[line_index]
            if cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_START_INDICATOR']):
                self.script_start_time = logprocessinglibrary.get_timestamp_by_line(cur_ae_log_line)
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_EXITCODE_INDICATOR']):
                start_index = len(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_EXITCODE_INDICATOR'])
                end_index = cur_ae_log_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                self.exit_code = int(cur_ae_log_line[start_index: end_index])
                self.script_stop_time = logprocessinglibrary.get_timestamp_by_line(cur_ae_log_line)
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_ERROR_INDICATOR']):
                self.error_message = self.error_message + cur_ae_log_line[len(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_ERROR_INDICATOR']):] + "\n"
                line_index = line_index + 1
                while line_index < self.agent_executor_log_len:
                    if self.agent_executor_log_list[line_index].startswith(self.log_keyword_table['LOG_ENDING_STRING']):
                        break
                    self.error_message = self.error_message + self.agent_executor_log_list[line_index] + "\n"
                    line_index = line_index + 1
                while self.error_message.endswith("\n"):
                    self.error_message = self.error_message[:-1]
                continue
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_OUTPUT_INDICATOR']):
                self.output = self.output + cur_ae_log_line[len(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_OUTPUT_INDICATOR']):] + "\n"
                line_index = line_index + 1
                while line_index < self.agent_executor_log_len:
                    if self.agent_executor_log_list[line_index].startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_OUTPUT_END_INDICATOR']):
                        break
                    self.output = self.output + self.agent_executor_log_list[line_index] + "\n"
                    line_index = line_index + 1
                while self.output.endswith("\n"):
                    self.output = self.output[:-1]
                continue

            line_index = line_index + 1

    def generate_powershell_log_output(self):
        interpreted_log_output = ""

        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('Script ID:',
                                                                                                         self.script_id))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Script Context:',
                self.context))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Executing User ID:',
                str(self.script_exec_user_id)))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Script Signature Required:',
                str(self.sig_check)))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('Execution Result:',
                                                                                                         str(self.execution_result)))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('Exit Code:',
                                                                                                         str(self.exit_code)))

        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Execution Start Time:',
                self.script_start_time))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Execution Stop Time:',
                self.script_stop_time))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Error Message:',
                self.error_message))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Script Output:',
                self.output))

        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('Script Body:',
                                                                                                         ""))

        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(self.script_body)
        return interpreted_log_output

