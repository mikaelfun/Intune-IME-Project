"""
This is Class def for EMS life cycle.
Each log interpret request may contain multiple EMS life cycles due to reboot, service restarts.
Create this class object for each EMS life cycle.

Error Code range: 2000 - 2999

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
import applicationpoller
import powershell
import remediation
import scriptpoller


class EMSLifeCycle:
    def __init__(self, ime_log, agent_executor_log, boot_reason="IME Service Starts"):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.ime_log = ime_log
        self.agent_executor_log = agent_executor_log
        self.boot_reason = boot_reason
        self.log_len = len(self.ime_log)
        self.app_poller_object_list = []
        self.ps_poller_object_list = []
        self.remediation_obejct_list = []
        self.poller_num = 0
        self.ps_poller_num = 0
        self.remediation_num = 0

        self.initialize_app_poller_object_list()
        self.initialize_ps_poller_object_list()
        self.initialize_remediation_object_list()

    def initialize_ps_poller_list(self):
        ps_poller_logs = []
        line_index_start_list = logprocessinglibrary.locate_line_startswith_keyword(self.ime_log,
                                                                                    self.log_keyword_table[
                                                                                        'LOG_PS_POLLER_START'])
        line_index_stop_list = logprocessinglibrary.locate_line_startswith_keyword(self.ime_log,
                                                                                   self.log_keyword_table[
                                                                                        'LOG_PS_POLLER_STOP'])
        while len(line_index_start_list) != 0 and len(line_index_stop_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_poller_thread = logprocessinglibrary.locate_thread(self.ime_log[cur_start_index])
            cur_poller_log = self.ime_log[cur_start_index]

            line_index_iter = cur_start_index + 1
            while line_index_iter < self.log_len:
                if line_index_iter in line_index_stop_list and cur_poller_thread == logprocessinglibrary.locate_thread(
                        self.ime_log[line_index_iter]):
                    # finds first poller stop line and thread id matches
                    cur_poller_log = cur_poller_log + self.ime_log[line_index_iter]
                    ps_poller_logs.append(cur_poller_log)
                    line_index_stop_list.remove(line_index_iter)
                    break
                elif self.ime_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']):
                    """
                    Fixing for Powershell have multiple threads logs in one app poller
                    """
                    thread_id_exception_headers = json.loads(self.log_keyword_table['LOG_PS_THREAD_ID_EXCEPTION_HEADERS'])
                    is_powershell_second_thread = False
                    for each_header in thread_id_exception_headers:
                        if self.ime_log[line_index_iter].startswith(each_header):
                            is_powershell_second_thread = True
                    if cur_poller_thread == logprocessinglibrary.locate_thread(
                            self.ime_log[line_index_iter]) or is_powershell_second_thread:
                        # normal log line with same thread id
                        cur_poller_log = cur_poller_log + self.ime_log[line_index_iter]

                    line_index_iter = line_index_iter + 1
                else:
                    line_index_iter = line_index_iter + 1

            if line_index_iter >= self.log_len:
                ps_poller_logs.append(cur_poller_log)

        if len(line_index_stop_list) != 0:
            # Dropping all
            line_index_stop_list.clear()

        if len(line_index_start_list) != 0:
            # forming the application poller session from start index to end of log.
            while len(line_index_start_list) > 0:
                each_start_index = line_index_start_list.pop()
                cur_poller_thread = logprocessinglibrary.locate_thread(self.ime_log[each_start_index])
                cur_poller_log = self.ime_log[each_start_index]
                line_index_iter = each_start_index
                while line_index_iter < self.log_len:
                    if self.ime_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']):
                        """
                        Fixing for Powershell have multiple threads logs in one app poller
                        """
                        thread_id_exception_headers = self.log_keyword_table['LOG_PS_THREAD_ID_EXCEPTION_HEADERS']
                        is_powershell_second_thread = False
                        for each_header in thread_id_exception_headers:
                            if self.ime_log[line_index_iter].startswith(each_header):
                                is_powershell_second_thread = True
                        if cur_poller_thread == logprocessinglibrary.locate_thread(
                                self.ime_log[line_index_iter]) or is_powershell_second_thread:
                            # normal log line with same thread id
                            cur_poller_log = cur_poller_log + self.ime_log[line_index_iter]

                        line_index_iter = line_index_iter + 1
                    else:
                        line_index_iter = line_index_iter + 1
                ps_poller_logs.append(cur_poller_log)

        return ps_poller_logs

    def initialize_ps_agent_executor_list(self):
        agent_executor_logs = []
        line_index_start_list = logprocessinglibrary.locate_line_startswith_keyword(self.agent_executor_log,
                                                                                    self.log_keyword_table[
                                                                                        'LOG_AGENTEXE_PS_SCRIPT_INDICATOR'])
        while len(line_index_start_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_ps_poller_log = ""
            # find the first line of "<![LOG[ExecutorLog AgentExecutor gets invoked" that is after the poller start index
            cur_index = cur_start_index
            while cur_index < len(self.agent_executor_log):
                cur_line = self.agent_executor_log[cur_index]
                if cur_line.startswith(self.log_keyword_table['LOG_AGENTEXE_SCRIPT_START_INDICATOR']):
                    break
                else:
                    cur_ps_poller_log = cur_ps_poller_log + cur_line
                    cur_index = cur_index + 1
            agent_executor_logs.append(cur_ps_poller_log)
        return agent_executor_logs

    def initialize_app_poller_list(self):
        # Input log Beginning from service starts, ending at service stop
        application_poller_logs = []
        application_poller_threads = []

        '''
        2 pointer
        worst case:
        start t=1
        start t=2
        start t=3
        stop  t=2
        stop  t=3
        stop  t=1


        '''
        line_index_start_list = logprocessinglibrary.locate_line_startswith_keyword(self.ime_log, self.log_keyword_table['LOG_APP_POLLER_START_STRING'])
        line_index_stop_list = logprocessinglibrary.locate_line_startswith_keyword(self.ime_log, self.log_keyword_table['LOG_APP_POLLER_STOP_STRING'])

        '''
        Consecutive start stop should have same thread ID. Dropping if thread ID is not match
         <![LOG[[Win32App] ----------------------------------------------------- application poller starts. ----------------------------------------------------- ]LOG]!><time="07:04:15.4880472" date="3-25-2023" component="IntuneManagementExtension" context="" type="2" thread="47" file="">
	     <![LOG[[Win32App] ----------------------------------------------------- application poller stopped. ----------------------------------------------------- ]LOG]!><time="12:04:17.0435845" date="3-25-2023" component="IntuneManagementExtension" context="" type="2" thread="47" file="">
        '''

        while len(line_index_start_list) != 0 and len(line_index_stop_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_poller_thread = logprocessinglibrary.locate_thread(self.ime_log[cur_start_index])
            cur_poller_log = self.ime_log[cur_start_index]
            application_poller_threads.append(cur_poller_thread)

            line_index_iter = cur_start_index + 1
            while line_index_iter < self.log_len:
                if line_index_iter in line_index_stop_list and cur_poller_thread == logprocessinglibrary.locate_thread(
                        self.ime_log[line_index_iter]):
                    # finds first poller stop line and thread id matches
                    cur_poller_log = cur_poller_log + self.ime_log[line_index_iter]
                    application_poller_logs.append(cur_poller_log)
                    line_index_stop_list.remove(line_index_iter)
                    break
                elif self.ime_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']):
                    """
                    Fixing for UWP app have multiple threads logs in one app poller
                    """
                    thread_id_exception_headers = self.log_keyword_table['LOG_MSFB_THREAD_ID_EXCEPTION_HEADERS']
                    is_msfb_second_thread = False
                    for each_header in thread_id_exception_headers:
                        if self.ime_log[line_index_iter].startswith(each_header):
                            is_msfb_second_thread = True
                    if cur_poller_thread == logprocessinglibrary.locate_thread(self.ime_log[line_index_iter]) or is_msfb_second_thread:
                        # normal log line with same thread id
                        cur_poller_log = cur_poller_log + self.ime_log[line_index_iter]

                    line_index_iter = line_index_iter + 1
                else:
                    line_index_iter = line_index_iter + 1

            if line_index_iter >= self.log_len:
                application_poller_logs.append(cur_poller_log)

        if len(line_index_stop_list) != 0:
            # Dropping all
            line_index_stop_list.clear()

        if len(line_index_start_list) != 0:
            # forming the application poller session from start index to end of log.
            while len(line_index_start_list) > 0:
                each_start_index = line_index_start_list.pop()
                cur_poller_thread = logprocessinglibrary.locate_thread(self.ime_log[each_start_index])
                application_poller_threads.append(cur_poller_thread)
                cur_poller_log = self.ime_log[each_start_index]
                line_index_iter = each_start_index
                while line_index_iter < self.log_len:
                    if self.ime_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']):
                        """
                        Fixing for UWP app have multiple threads logs in one app poller
                        """
                        thread_id_exception_headers = self.log_keyword_table['LOG_MSFB_THREAD_ID_EXCEPTION_HEADERS']
                        is_msfb_second_thread = False
                        for each_header in thread_id_exception_headers:
                            if self.ime_log[line_index_iter].startswith(each_header):
                                is_msfb_second_thread = True
                        if cur_poller_thread == logprocessinglibrary.locate_thread(
                                self.ime_log[line_index_iter]) or is_msfb_second_thread:
                            # normal log line with same thread id
                            cur_poller_log = cur_poller_log + self.ime_log[line_index_iter]

                        line_index_iter = line_index_iter + 1
                    else:
                        line_index_iter = line_index_iter + 1
                application_poller_logs.append(cur_poller_log)

        return application_poller_logs, application_poller_threads

    def initialize_app_poller_object_list(self):
        app_poller_log_list, app_poller_thread_list = self.initialize_app_poller_list()
        self.poller_num = len(app_poller_log_list)
        for index_app_poller_log in range(self.poller_num):
            self.app_poller_object_list.append(applicationpoller.ApplicationPoller(app_poller_log_list[index_app_poller_log],
                                                                 app_poller_thread_list[index_app_poller_log]))

    def initialize_ps_poller_object_list(self):
        ps_poller_log_list = self.initialize_ps_poller_list()
        agent_executor_log_list = self.initialize_ps_agent_executor_list()
        self.ps_poller_num = len(ps_poller_log_list)
        for index_ps_poller_log in range(self.ps_poller_num):
            self.ps_poller_object_list.append(scriptpoller.ScriptPoller(ps_poller_log_list[index_ps_poller_log], agent_executor_log_list))

    def initialize_remediation_ime_list(self):
        ime_remediation_log_list = []
        line_index_start_list = logprocessinglibrary.locate_line_startswith_keyword(self.ime_log,
                                                                                    self.log_keyword_table[
                                                                                        'LOG_IME_REMEDIATION_SCRIPT_FILE_INDICATOR'])
        while len(line_index_start_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_remediation_thread = logprocessinglibrary.locate_thread(self.ime_log[cur_start_index])
            cur_remediation_log = ""
            # find the first line of "<![LOG[Powershell execution is done" of same thread ID that is after the remediation start index
            cur_index = cur_start_index
            while cur_index < len(self.ime_log):
                cur_line = self.ime_log[cur_index]
                cur_thread = logprocessinglibrary.locate_thread(cur_line)
                if cur_thread != cur_remediation_thread:
                    cur_index = cur_index + 1
                    continue
                if cur_line.startswith(self.log_keyword_table['LOG_IME_REMEDIATION_SCRIPT_END_INDICATOR']):
                    break
                else:
                    cur_remediation_log = cur_remediation_log + cur_line
                    cur_index = cur_index + 1
            ime_remediation_log_list.append(cur_remediation_log)
        return ime_remediation_log_list

    def initialize_remediation_agent_executor_list(self):
        ae_remediation_log_list = []
        line_index_start_list = logprocessinglibrary.locate_line_startswith_keyword(self.agent_executor_log,
                                                                                    self.log_keyword_table[
                                                                                        'LOG_AGENTEXE_REMEDIATION_SCRIPT_START_INDICATOR'])
        while len(line_index_start_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_remediation_log = ""
            # find the first line of "<![LOG[ExecutorLog AgentExecutor gets invoked" that is after the poller start index
            cur_index = cur_start_index
            while cur_index < len(self.agent_executor_log):
                cur_line = self.agent_executor_log[cur_index]
                if cur_line.startswith(self.log_keyword_table['LOG_AGENTEXE_SCRIPT_START_INDICATOR']):
                    break
                else:
                    cur_remediation_log = cur_remediation_log + cur_line
                    cur_index = cur_index + 1
            ae_remediation_log_list.append(cur_remediation_log)
        return ae_remediation_log_list

    def initialize_remediation_object_list(self):
        ime_remediation_log_list = self.initialize_remediation_ime_list()
        agent_executor_remediation_log_list = self.initialize_remediation_agent_executor_list()
        if len(ime_remediation_log_list) != len(agent_executor_remediation_log_list):
            print("IME log may be missing remediation log")
        self.remediation_num = min(len(agent_executor_remediation_log_list), len(ime_remediation_log_list))
        for index_remediation_log in range(self.remediation_num):
            self.remediation_obejct_list.append(
                remediation.Remediation(agent_executor_remediation_log_list[-self.remediation_num:][index_remediation_log], ime_remediation_log_list[-self.remediation_num:][index_remediation_log]))

    def generate_ems_win32_lifecycle_log_output(self, show_full_log):
        interpreted_log_output = ""
        for cur_app_poller_log_index in range(self.poller_num):
            cur_app_poller_log = self.app_poller_object_list[cur_app_poller_log_index]
            ems_win32_lifecycle_log_output = cur_app_poller_log.generate_application_poller_log_output(show_full_log)
            if ems_win32_lifecycle_log_output != "":
                interpreted_log_output += ems_win32_lifecycle_log_output
                interpreted_log_output += '\n'
        return interpreted_log_output

    def generate_ems_powershell_lifecycle_log_output(self):
        interpreted_log_output = ""
        for cur_ps_poller_log_index in range(self.ps_poller_num):
            cur_ps_poller_log = self.ps_poller_object_list[cur_ps_poller_log_index]
            ems_ps_lifecycle_log_output = cur_ps_poller_log.generate_powershell_poller_log_output()
            if ems_ps_lifecycle_log_output != "":
                interpreted_log_output += ems_ps_lifecycle_log_output
                interpreted_log_output += '\n'
        return interpreted_log_output

    def generate_ems_remediation_lifecycle_log_output(self):
        interpreted_log_output = ""
        for cur_remediation_log_index in range(self.remediation_num):
            cur_remediation_log = self.remediation_obejct_list[cur_remediation_log_index]
            ems_remediation_log_output = cur_remediation_log.generate_remediation_log_output()
            if ems_remediation_log_output != "":
                interpreted_log_output += ems_remediation_log_output
                interpreted_log_output += '\n'
        return interpreted_log_output
