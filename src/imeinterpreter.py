"""
This is root Class def for IME interpreter.
As service app, it will process multiple interpret requests at the same time.
Create this class object for each request.

Error Code range: 1000 - 1999

Class hierarchy:
- ImeInterpreter
    - EMSLifeCycle
        - ApplicationPoller
            - SubGraph
                - Win32App

"""
import os
import datetime
import logprocessinglibrary
import emslifecycle
import constructinterpretedlog


class ImeInterpreter:
    def __init__(self, log_folder_path):
        self.log_folder_path = log_folder_path
        self.life_cycle_list = []

        self.full_log = self.load_full_logs()  # full log as line of string list
        self.initialize_life_cycle_list()
        self.life_cycle_num = len(self.life_cycle_list)

    def save_log_to_service(self):
        # saving uploaded log locally for further improvement
        pass

    def open_log_file(self, log_path):
        try:
            log_file = open(log_path, mode='r', encoding='utf-8-sig')
            log_as_lines = log_file.readlines()
            log_file.close()
        except:
            print("Unable to load log via utf-8")
            try:
                log_file = open(log_path, mode='r', encoding='ISO-8859-1')
                log_as_lines = log_file.readlines()
                log_file.close()
            except:
                print("Unable to load log via ISO-8859-1")
                log_as_lines = ""
        return log_as_lines

    def load_all_ime_logs(self):
        # Listing older IME logs
        dir_list = os.listdir(self.log_folder_path)
        # filtering IME logs only
        dir_list = [i for i in dir_list if i.lower().startswith('intunemanagementextension') and i.endswith('.log')]
        # Remove Current IME log, which is most recent
        if 'intunemanagementextension.log' in dir_list:
            dir_list.remove('intunemanagementextension.log')
        elif 'IntuneManagementExtension.log' in dir_list:
            dir_list.remove('IntuneManagementExtension.log')
        else:
            print("Error! Path does not contain IntuneManagementExtension.log! Exit 1.1")
            return None
        # print(dir_list)
        # Sorting based on date in file name, first log should be the oldest log
        sorted(dir_list)
        # print(dir_list)
        full_log = []
        for each_log in dir_list:
            current_log_file_path = self.log_folder_path + '\\' + each_log
            current_ime_log_as_lines = self.open_log_file(current_log_file_path)
            full_log = full_log + current_ime_log_as_lines
            '''
            There is an issue that sometimes after concatenating 2 log files, the EMS Agent stop will be missing.
            Force adding at the beginning.
            '''
        ime_log_file_path = self.log_folder_path + '\\IntuneManagementExtension.log'
        ime_log_file_lower_path = self.log_folder_path + '\\intunemanagementextension.log'

        if not (os.path.isfile(ime_log_file_path)):
            ime_log_file_path = ime_log_file_lower_path
            if not (os.path.isfile(ime_log_file_lower_path)):
                print("Error! Path does not contain IntuneManagementExtension.log! Exit 1.0")
                return None
            # exit(1100)
        most_recent_log_file_as_lines = self.open_log_file(ime_log_file_path)
        if most_recent_log_file_as_lines[0].startswith('<![LOG[EMS Agent Started]') and len(full_log) > 0 and not full_log[
            -1].startswith('<![LOG[EMS Agent Stopped]'):
            post_part_start_index = full_log[-1].find('LOG]!>')
            made_up_line = '<![LOG[EMS Agent Stopped]LOG]!>' + full_log[-1][post_part_start_index + 6:]
            most_recent_log_file_as_lines.insert(0, made_up_line)
        full_log = full_log + most_recent_log_file_as_lines
        return full_log

    def merge_ime_and_app_workload_logs(self, ime_logs, app_workload_logs):
        full_log = []
        left, right = 0, 0

        ime_log_len = len(ime_logs)
        app_workload_log_len = len(app_workload_logs)

        while left < ime_log_len and right < app_workload_log_len:
            left_line = ime_logs[left]
            right_line = app_workload_logs[right]
            left_time = logprocessinglibrary.get_timestamp_by_line(left_line)
            right_time = logprocessinglibrary.get_timestamp_by_line(right_line)
            if left_time > right_time:
                full_log.append(right_line)
                right = right + 1
            else:
                full_log.append(left_line)
                left = left + 1

        while left < ime_log_len:
            full_log.append(ime_logs[left])
            left = left + 1
        while right < app_workload_log_len:
            full_log.append(app_workload_logs[right])
            right = right + 1
        # with open('C:\\temp\\temp\\imeout.log', 'w') as outfile:
        #     for i in range(len(full_log)):
        #         outfile.writelines(full_log[i])
        return full_log

    def load_all_app_workload_logs(self):
        """
        Fix the change in log structure in 2407 that Win32 log entries are separated into AppWorkload.log
        Adding the ability to merge the separated logs if exists.
        """
        app_workload_log_file_path = self.log_folder_path + '\\AppWorkload.log'
        app_workload_log_lower_file_path = self.log_folder_path + '\\appworkload.log'

        dir_list = os.listdir(self.log_folder_path)
        # filtering AppWorkload logs only
        dir_list = [i for i in dir_list if i.lower().startswith('AppWorkload') and i.endswith('.log')]
        # Remove Current IME log, which is most recent
        if 'appworkload.log' in dir_list:
            dir_list.remove('appworkload.log')
        elif 'AppWorkload.log' in dir_list:
            dir_list.remove('AppWorkload.log')
        else:
            # print("Error! Path does not contain AppWorkload.log! Exit 1.2")
            pass
        # print(dir_list)
        # Sorting based on date in file name, first log should be the oldest log
        sorted(dir_list)
        # print(dir_list)
        full_log = []
        for each_log in dir_list:
            current_log_file_path = self.log_folder_path + '\\' + each_log
            current_app_workload_log_as_lines = self.open_log_file(current_log_file_path)
            full_log = full_log + current_app_workload_log_as_lines
            '''
            There is an issue that sometimes after concatenating 2 log files, the EMS Agent stop will be missing.
            Force adding at the beginning.
            '''

        if not (os.path.isfile(app_workload_log_file_path)):
            app_workload_log_file_path = app_workload_log_lower_file_path
            if not (os.path.isfile(app_workload_log_lower_file_path)):
                print("Error! Path does not contain AppWorkload.log! Exit 1.3")
                return full_log
            # exit(1100)
        most_recent_log_file_as_lines = self.open_log_file(app_workload_log_file_path)

        full_log = full_log + most_recent_log_file_as_lines
        return full_log

    def load_full_logs(self):
        app_workload_log_file_path = self.log_folder_path + '\\AppWorkload.log'
        app_workload_log_lower_file_path = self.log_folder_path + '\\appworkload.log'

        app_workload_log_exists = (os.path.isfile(app_workload_log_file_path)) or (os.path.isfile(app_workload_log_lower_file_path))

        if not app_workload_log_exists:
            full_log = self.load_all_ime_logs()
            """
            Handled lines without thread here, before passing to emslifecyle process.
            Merged breaking lines into 1 line with |
            """
            ime_logs = logprocessinglibrary.process_breaking_line_log(full_log)
            return ime_logs
        else:
            ime_log = self.load_all_ime_logs()
            app_workload_log = self.load_all_app_workload_logs()
            """
            Handled lines without thread here, before passing to emslifecyle process.
            Merged breaking lines into 1 line with |
            """
            ime_logs = logprocessinglibrary.process_breaking_line_log(ime_log)
            app_workload_logs = logprocessinglibrary.process_breaking_line_log(app_workload_log)
            full_log = self.merge_ime_and_app_workload_logs(ime_logs, app_workload_logs)
            return full_log

    def separate_log_into_service_lifecycle(self):
        ems_agent_start_lines = []
        ems_agent_stop_lines = []
        ems_agent_start_string = '<![LOG[EMS Agent Started]'
        ems_agent_stop_string = '<![LOG[EMS Agent Stopped]'
        full_log_len = len(self.full_log)
        for index in range(full_log_len):
            cur_line = self.full_log[index]
            if cur_line.startswith(ems_agent_start_string):
                ems_agent_start_lines.append(index)
            elif cur_line.startswith(ems_agent_stop_string):
                ems_agent_stop_lines.append(index)
        start_lines_len = len(ems_agent_start_lines)
        stop_lines_len = len(ems_agent_stop_lines)
        last_start_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[0])
        last_stop_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[-1])
        if start_lines_len > 0:
            last_start_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[ems_agent_start_lines[-1]])
        if stop_lines_len > 0:
            last_stop_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[ems_agent_stop_lines[-1]])

        ems_agent_sorted_start_lines = []
        ems_agent_sorted_stop_lines = []

        start_line_index = 0
        stop_line_index = 0


        """
        This situation cannot exist:
        EMS AGENT stops
        EMS AGENT stops
        
        This situation can exist: (hard reboot)
        EMS AGENT starts
        EMS AGENT starts
        """
        while start_line_index < start_lines_len and stop_line_index < stop_lines_len:
            cur_start_line_top_index = ems_agent_start_lines[start_line_index]
            cur_stop_line_top_index = ems_agent_stop_lines[stop_line_index]
            if cur_start_line_top_index < cur_stop_line_top_index:
                ems_agent_sorted_start_lines.append(cur_start_line_top_index)
                start_line_index += 1
                if start_line_index < start_lines_len:
                    if ems_agent_start_lines[start_line_index] < ems_agent_stop_lines[stop_line_index]:
                        """
                        start
                        start
                        stop
                        """
                        ems_agent_sorted_stop_lines.append(ems_agent_start_lines[start_line_index] - 1)
                    else:
                        """
                        start
                        stop
                        start
                        """
                        ems_agent_sorted_stop_lines.append(ems_agent_stop_lines[stop_line_index])
                        stop_line_index += 1
                else:
                    ems_agent_sorted_stop_lines.append(ems_agent_stop_lines[stop_line_index])
            else:
                ems_agent_sorted_start_lines.append(0)
                ems_agent_sorted_stop_lines.append(cur_stop_line_top_index)
                stop_line_index += 1

        if start_line_index < start_lines_len:
            """
            Start
            ...
            """
            while start_line_index < start_lines_len:
                ems_agent_sorted_start_lines.append(ems_agent_start_lines[start_line_index])
                start_line_index += 1
                if start_line_index < start_lines_len:
                    ems_agent_sorted_stop_lines.append(ems_agent_start_lines[start_line_index] - 1)
                else:
                    ems_agent_sorted_stop_lines.append(full_log_len-1)
        elif stop_line_index < stop_lines_len:
            pass
        elif start_line_index == start_lines_len and stop_line_index == stop_lines_len:
            ems_agent_sorted_start_lines.append(0)
            ems_agent_sorted_stop_lines.append(full_log_len - 1)

        ems_agent_lifecycle_log_list = []
        # Indicating whether the service is being restarted manually or restart by reboot
        agent_life_ending_reason = ["IME Service Starts"]  # first one is always IME service Starts

        for agent_lifecycle_log_index in range(len(ems_agent_sorted_start_lines)):
            ems_agent_lifecycle_log_list.append(
                self.full_log[ems_agent_sorted_start_lines[agent_lifecycle_log_index]:
                              ems_agent_sorted_stop_lines[agent_lifecycle_log_index]])
            if agent_lifecycle_log_index < len(ems_agent_sorted_start_lines) - 1:
                agent_stop_time = logprocessinglibrary.get_timestamp_by_line(self.full_log[ems_agent_sorted_stop_lines[agent_lifecycle_log_index]])
                agent_stop_time_datetime = datetime.datetime.strptime(agent_stop_time[:-4], '%m-%d-%Y %H:%M:%S')
                agent_next_start_time = logprocessinglibrary.get_timestamp_by_line(
                    self.full_log[ems_agent_sorted_start_lines[agent_lifecycle_log_index + 1]])
                agent_next_start_time_datetime = logprocessinglibrary.convert_date_string_to_date_time(agent_next_start_time[:-4])

                if agent_next_start_time_datetime - agent_stop_time_datetime < datetime.timedelta(seconds=10):
                    agent_life_ending_reason.append("Service Manual Restart")
                else:
                    agent_life_ending_reason.append("Device Reboot")

        return ems_agent_lifecycle_log_list, agent_life_ending_reason

    def initialize_life_cycle_list(self):
        if self.full_log is None:
            return None
        ems_agent_lifecycle_log_list, ems_agent_restart_reasons = \
            self.separate_log_into_service_lifecycle()
        if len(ems_agent_lifecycle_log_list) != len(ems_agent_restart_reasons):
            print("Error len(ems_agent_lifecycle_log_list) != len(ems_agent_restart_reasons)")
            return None
            # exit(1000)
        for index_lifecycle_log in range(len(ems_agent_lifecycle_log_list)):
            self.life_cycle_list.append(emslifecycle.EMSLifeCycle(ems_agent_lifecycle_log_list[index_lifecycle_log],
                                        ems_agent_restart_reasons[index_lifecycle_log]))

    def generate_ime_interpreter_log_output(self, show_not_expired_subgraph=False):
        interpreted_log_output = ""
        if self.full_log is None:
            interpreted_log_output += "Error! Path does not contain IntuneManagementExtension.log!"
            return interpreted_log_output
        for cur_lifecycle_log_index in range(self.life_cycle_num):
            cur_lifecycle_log = self.life_cycle_list[cur_lifecycle_log_index]
            """
            +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++IME Service Starts+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            """
            interpreted_log_output += constructinterpretedlog.write_ime_service_start_by_reason(cur_lifecycle_log.boot_reason)
            interpreted_log_output += '\n'
            interpreted_log_output += cur_lifecycle_log.generate_ems_lifecycle_log_output(show_not_expired_subgraph)

        return interpreted_log_output





