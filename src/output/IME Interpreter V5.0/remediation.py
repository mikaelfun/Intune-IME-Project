import constructinterpretedlog
import logprocessinglibrary


class Remediation:
    def __init__(self, agent_executor_remediation_log, ime_remediation_log):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.ae_log = list(agent_executor_remediation_log.split("\n"))
        if self.ae_log[-1] == "":
            self.ae_log.pop(-1)
        self.agent_executor_log_len = len(self.ae_log)
        self.ime_log = list(ime_remediation_log.split("\n"))
        if self.ime_log[-1] == "":
            self.ime_log.pop(-1)
        self.ime_log_len = len(self.ime_log)

        self.script_id = ""
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.ime_log[0])
        self.stop_time = logprocessinglibrary.get_timestamp_by_line(self.ime_log[-1])

        self.script_exec_user_id = ""
        self.context = "Unknown"
        self.bit32or64 = -1
        self.exit_code = "Unknown"
        self.sig_check = False
        self.error_message = ""
        self.output = ""
        self.script_start_time = ""
        self.script_stop_time = ""
        self.execution_result = "Unknown"
        self.detect_or_remediate = "Unknown"

        self.interpret_remediation_log()

    def interpret_remediation_log(self):
        for line_index in range(self.ime_log_len):
            cur_ime_line = self.ime_log[line_index]
            if cur_ime_line.startswith(self.log_keyword_table['LOG_IME_REMEDIATION_SCRIPT_USER_INDICATOR']):
                self.context = "User"
            elif cur_ime_line.startswith(self.log_keyword_table['LOG_IME_REMEDIATION_SCRIPT_SYSTEM_INDICATOR']):
                self.context = "System"

        line_index = 0
        while line_index < self.agent_executor_log_len:
            cur_ae_log_line = self.ae_log[line_index]
            if cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_REMEDIATION_SCRIPT_START_INDICATOR']):
                self.script_id = logprocessinglibrary.find_app_id_with_starting_string(cur_ae_log_line,
                                                                                                 self.log_keyword_table[
                                                                                                     'LOG_AGENTEXE_REMEDIATION_SCRIPT_START_INDICATOR'])
                if 'detect.ps1' in cur_ae_log_line:
                    self.detect_or_remediate = "Detect"
                elif 'remediate.ps1' in cur_ae_log_line:
                    self.detect_or_remediate = "Remediate"

            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_REMEDIATION_SCRIPT_32BIT_INDICATOR']):
                self.bit32or64 = "32-BIT"
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_REMEDIATION_SCRIPT_64BIT_INDICATOR']):
                self.bit32or64 = "64-BIT"
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_START_INDICATOR']):
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
                    if self.ae_log[line_index].startswith(self.log_keyword_table['LOG_ENDING_STRING']):
                        break
                    self.error_message = self.error_message + self.ae_log[line_index] + "\n"
                    line_index = line_index + 1
                while self.error_message.endswith("\n"):
                    self.error_message = self.error_message[:-1]
                continue
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_OUTPUT_INDICATOR']):
                self.output = self.output + cur_ae_log_line[len(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_OUTPUT_INDICATOR']):] + "\n"
                line_index = line_index + 1
                while line_index < self.agent_executor_log_len:
                    if self.ae_log[line_index].startswith(self.log_keyword_table['LOG_AGENTEXE_PS_SCRIPT_OUTPUT_END_INDICATOR']):
                        break
                    self.output = self.output + self.ae_log[line_index] + "\n"
                    line_index = line_index + 1
                while self.output.endswith("\n"):
                    self.output = self.output[:-1]
                continue
            elif cur_ae_log_line.startswith(self.log_keyword_table['LOG_AGENTEXE_REMEDIATION_SCRIPT_RESULT_INDICATOR']):
                start_index = len(self.log_keyword_table['LOG_AGENTEXE_REMEDIATION_SCRIPT_RESULT_INDICATOR'])
                stop_index = cur_ae_log_line.find(self.log_keyword_table['LOG_ENDING_STRING'])
                line_result = cur_ae_log_line[start_index: stop_index]
                if line_result == "failed to execute":
                    self.execution_result = "Fail"
                elif line_result == "successfully executed.":
                    self.execution_result = "Success"

            line_index = line_index + 1

    def generate_remediation_log_output(self):
        interpreted_log_output = ""

        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output('Script ID:',
                                                                                                         self.script_id))
        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Script Mode:',
                self.detect_or_remediate))

        interpreted_log_output += constructinterpretedlog.write_log_output_line_without_indent_depth(
            constructinterpretedlog.write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(
                'Script Context:',
                self.context))
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

        return interpreted_log_output
