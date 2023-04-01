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
from logprocessinglibrary import *
from emslifecycle import *
from constructinterpretedlog import *
import sys


class ImeInterpreter:
    def __init__(self, log_folder_path):
        self.log_folder_path = log_folder_path
        self.life_cycle_list = []

        self.full_log = self.load_all_ime_logs()  # full log as line of string list
        self.initialize_life_cycle_list()
        self.life_cycle_num = len(self.life_cycle_list)

    def save_log_to_service(self):
        # saving uploaded log locally for further improvement
        pass

    def load_all_ime_logs(self):
        ime_log_file_path = self.log_folder_path + '\\IntuneManagementExtension.log'
        if not (os.path.isfile(ime_log_file_path)):
            print("Error! Path does not contain IntuneManagementExtension.log! Exit 1.0")
            return None
            #exit(1100)
        current_log_file = open(ime_log_file_path, mode='r', encoding='utf-8-sig')
        current_ime_log_as_lines = current_log_file.readlines()
        full_log = []
        current_log_file.close()

        dir_list = os.listdir(self.log_folder_path)
        dir_list = [i for i in dir_list if i.startswith('IntuneManagementExtension') and i.endswith('.log')]
        dir_list.remove('IntuneManagementExtension.log')
        #print(dir_list)
        sorted(dir_list)
        #print(dir_list)
        for each_log in dir_list:
            current_log_file_path = self.log_folder_path + '\\' + each_log
            current_log_file = open(current_log_file_path, mode='r', encoding='utf-8-sig')
            current_log_as_lines = current_log_file.readlines()
            '''
            There is an issue that sometimes after concatenating 2 log files, the EMS Agent stop will be missing.
            Force adding at the beginning.
            '''
            if current_log_as_lines[0].startswith('<![LOG[EMS Agent Started]') and len(full_log) > 0 and not full_log[-1].startswith('<![LOG[EMS Agent Stopped]'):
                post_part_start_index = full_log[-1].find('LOG]!>')
                made_up_line = '<![LOG[EMS Agent Stopped]LOG]!>' + full_log[-1][post_part_start_index + 6:]
                current_log_as_lines.insert(0, made_up_line)
            full_log = full_log + current_log_as_lines
            current_log_file.close()

        full_log = full_log + current_ime_log_as_lines
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
        last_start_time = get_timestamp_by_line(self.full_log[0])
        last_stop_time = get_timestamp_by_line(self.full_log[-1])
        if start_lines_len > 0:
            last_start_time = get_timestamp_by_line(self.full_log[ems_agent_start_lines[-1]])
        if stop_lines_len > 0:
            last_stop_time = get_timestamp_by_line(self.full_log[ems_agent_stop_lines[-1]])

        if start_lines_len == stop_lines_len + 1:
            '''
            Most ideal structure:
            <![LOG[EMS Agent Started]
            ...
            <![LOG[EMS Agent Stopped]
            ...
            <![LOG[EMS Agent Started]
            '''
            if last_start_time > last_stop_time:
                # This would mean that upon log collection, IME service is up and running,
                # so there is 1 more start than stop
                ems_agent_stop_lines.append(full_log_len)
            else:
                print("Error Invalid log structure! Exit 1201")
                return None
                #exit(1101)
        elif start_lines_len == stop_lines_len:
            if last_start_time < last_stop_time:
                # This would mean that upon log collection, IME service is stopped
                '''
                Like this structure:
                <![LOG[EMS Agent Started]
                ...
                <![LOG[EMS Agent Stopped]
                ...
                <![LOG[EMS Agent Started]
                ...
                <![LOG[EMS Agent Stopped]
                '''
                if start_lines_len == 0:
                    ems_agent_start_lines.append(0)
                    ems_agent_stop_lines.append(-1)
                    start_lines_len = len(ems_agent_start_lines)
                    stop_lines_len = len(ems_agent_stop_lines)
            else:
                # This would mean that upon log collection, IME service is up and running,
                # adding the first line as Starting, adding the last line as stopping
                '''
                This structure would apply when only recent IME logs are captured, 
                does not include to the very beginning of the log.
                Like IntuneManagementExtention.log alone
                <![LOG[EMS Agent Stopped]
                ...
                <![LOG[EMS Agent Started]
                ...
                <![LOG[EMS Agent Stopped]
                ...
                <![LOG[EMS Agent Started]
                '''
                ems_agent_start_lines.append(0)
                ems_agent_stop_lines.append(full_log_len)
        elif start_lines_len == stop_lines_len - 1:  # start_lines_len == stop_lines_len - 1
            '''
            Like this structure:
            <![LOG[EMS Agent Stopped]
            ...
            <![LOG[EMS Agent Started]
            ...
            <![LOG[EMS Agent Stopped]
            ...
            <![LOG[EMS Agent Started]
            ...
            <![LOG[EMS Agent Stopped]
            '''
            if last_start_time < last_stop_time:
                ems_agent_start_lines.append(0)
            else:
                print("Error Invalid log structure! Exit 1202")
                return None
                #exit(1102)
        elif start_lines_len > stop_lines_len + 1:
            '''
            Like this structure:
            <![LOG[EMS Agent Started]
            ...
            <![LOG[EMS Agent Stopped]
            ...
            <![LOG[EMS Agent Started]
            ...
            <![LOG[EMS Agent Started]
            '''
            while start_lines_len > len(ems_agent_stop_lines) + 1:
                diff = start_lines_len - len(ems_agent_stop_lines)
                ems_agent_stop_lines.append(ems_agent_start_lines[1 - diff] - 1)

            ems_agent_stop_lines.append(full_log_len)

        ems_agent_lifecycle_log_list = []
        # Indicating whether the service is being restarted manually or restart by reboot
        agent_life_ending_reason = ["IME Service Starts"]  # first one is always IME service Starts

        for agent_lifecycle_log_index in range(len(ems_agent_start_lines)):
            ems_agent_lifecycle_log_list.append(
                self.full_log[ems_agent_start_lines[agent_lifecycle_log_index]:
                              ems_agent_stop_lines[agent_lifecycle_log_index]])
            if agent_lifecycle_log_index < len(ems_agent_start_lines) - 1:
                agent_stop_time = get_timestamp_by_line(self.full_log[ems_agent_stop_lines[agent_lifecycle_log_index]])
                agent_stop_time_datetime = datetime.datetime.strptime(agent_stop_time[:-4], '%m-%d-%Y %H:%M:%S')
                agent_next_start_time = get_timestamp_by_line(
                    self.full_log[ems_agent_start_lines[agent_lifecycle_log_index + 1]])
                agent_next_start_time_datetime = convert_date_string_to_date_time(agent_next_start_time[:-4])

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
            self.life_cycle_list.append(EMSLifeCycle(ems_agent_lifecycle_log_list[index_lifecycle_log],
                                        ems_agent_restart_reasons[index_lifecycle_log]))

    def generate_ime_interpreter_log_output(self, show_not_expired_subgraph=True):
        interpreted_log_output = ""
        for cur_lifecycle_log_index in range(self.life_cycle_num):
            cur_lifecycle_log = self.life_cycle_list[cur_lifecycle_log_index]
            """
            +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++IME Service Starts+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            """
            interpreted_log_output += write_ime_service_start_by_reason(cur_lifecycle_log.boot_reason)
            interpreted_log_output += '\n'
            interpreted_log_output += cur_lifecycle_log.generate_ems_lifecycle_log_output(show_not_expired_subgraph)

        return interpreted_log_output


def get_args(name='default', first_argument='', second_argument=False):
    return first_argument,second_argument


if __name__ == '__main__':
    arguments = get_args(*sys.argv)
    a = ImeInterpreter(arguments[0])
    if arguments[1] == "True":
        print(a.generate_ime_interpreter_log_output(True))
    else:
        print(a.generate_ime_interpreter_log_output(False))

