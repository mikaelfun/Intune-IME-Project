"""
This is Class def for EMS life cycle.
Each log interpret request may contain multiple EMS life cycles due to reboot, service restarts.
Create this class object for each EMS life cycle.

Error Code range: 2000 - 2999

Class hierarchy:
- ImeInterpreter
    - EMSLifeCycle
        - ApplicationPoller
            - SubGraph
                - Win32App

"""
from logprocessinglibrary import *
from applicationpoller import *


class EMSLifeCycle:
    def __init__(self, full_log, boot_reason="IME Service Starts"):
        self.full_log = full_log
        self.boot_reason = boot_reason
        self.log_len = len(self.full_log)
        self.app_poller_object_list = []
        self.poller_num = 0

        self.initialize_app_poller_object_list()

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
        line_index_start_list = locate_line_startswith_keyword(
            self.full_log,
            '<![LOG[[Win32App] ----------------------------------------------------- application poller starts.')
        line_index_stop_list = locate_line_startswith_keyword(
            self.full_log,
            '<![LOG[[Win32App] ----------------------------------------------------- application poller stopped.')

        '''
        Consecutive start stop should have same thread ID. Dropping if thread ID is not match
         <![LOG[[Win32App] ----------------------------------------------------- application poller starts. ----------------------------------------------------- ]LOG]!><time="07:04:15.4880472" date="3-25-2023" component="IntuneManagementExtension" context="" type="2" thread="47" file="">
	     <![LOG[[Win32App] ----------------------------------------------------- application poller stopped. ----------------------------------------------------- ]LOG]!><time="12:04:17.0435845" date="3-25-2023" component="IntuneManagementExtension" context="" type="2" thread="47" file="">
        '''

        while len(line_index_start_list) != 0 and len(line_index_stop_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_poller_thread = locate_thread(self.full_log[cur_start_index])
            cur_poller_log = self.full_log[cur_start_index]
            application_poller_threads.append(cur_poller_thread)
            line_index_iter = cur_start_index + 1
            while line_index_iter < self.log_len:
                if line_index_iter in line_index_stop_list and cur_poller_thread == locate_thread(
                        self.full_log[line_index_iter]):
                    # finds first poller stop line and thread id matches
                    cur_poller_log = cur_poller_log + self.full_log[line_index_iter]
                    application_poller_logs.append(cur_poller_log)
                    line_index_stop_list.remove(line_index_iter)
                    break
                elif self.full_log[line_index_iter].startswith('<![LOG') and "-1" == locate_thread(
                        self.full_log[line_index_iter]):
                    # breaking log start line
                    temp_log = process_breaking_line_log(self.full_log[line_index_iter:])

                    if temp_log != "" and locate_thread(temp_log) == cur_poller_thread:
                        cur_poller_log = cur_poller_log + temp_log
                elif self.full_log[line_index_iter].startswith('<![LOG'):
                    # if cur_poller_thread == locate_thread(self.full_log[line_index_iter]):
                        # normal log line with same thread id
                    """
                    Fixing for UWP app have multiple threads logs in one app poller
                    """
                    cur_poller_log = cur_poller_log + self.full_log[line_index_iter]

                line_index_iter = line_index_iter + 1
            if line_index_iter == self.log_len:
                application_poller_logs.append(cur_poller_log)

        if len(line_index_stop_list) != 0:
            # Dropping all
            line_index_stop_list.clear()
            # while len(line_index_stop_list) > 0:
            #     each_stop_index = line_index_stop_list.pop()
            #     cur_poller_thread = locate_thread(self.full_log[each_stop_index])
            #     application_poller_threads.append(cur_poller_thread)
            #     cur_poller_log = self.full_log[each_stop_index]
            #     for line_index_iter in range(each_stop_index, -1, -1):
            #         # traversing backwards to beginning of log
            #         if cur_poller_thread == locate_thread(self.full_log[line_index_iter]):
            #             if self.full_log[line_index_iter].startswith('<![LOG'):
            #                 # normal log line with same thread id
            #                 cur_poller_log = self.full_log[line_index_iter] + cur_poller_log
            #             else:
            #                 # ending of line breaking log, do nothing and continue go backwards
            #                 continue
            #         elif self.full_log[line_index_iter].startswith('<![LOG') and "-1" == locate_thread(
            #                 self.full_log[line_index_iter]):
            #             # beginning of line breaking log, convert into one and append to beginning of current log
            #             temp_log = process_breaking_line_log(self.full_log[line_index_iter:])
            #             if temp_log != "" and locate_thread(temp_log) == cur_poller_thread:
            #                 cur_poller_log = temp_log + cur_poller_log
            #         else:
            #             # middle of line breaking log, do nothing.
            #             pass
            #     application_poller_logs.insert(0, cur_poller_log)
        if len(line_index_start_list) != 0:
            # forming the application poller session from start index to end of log.
            while len(line_index_start_list) > 0:
                each_start_index = line_index_start_list.pop()
                cur_poller_thread = locate_thread(self.full_log[each_start_index])
                application_poller_threads.append(cur_poller_thread)
                cur_poller_log = self.full_log[each_start_index]
                line_index_iter = each_start_index
                while line_index_iter < self.log_len:
                    if self.full_log[line_index_iter].startswith('<![LOG') and "-1" == locate_thread(
                            self.full_log[line_index_iter]):
                        # beginning of line breaking logs
                        temp_log = process_breaking_line_log(self.full_log[line_index_iter:])

                        if temp_log != "" and locate_thread(temp_log) == cur_poller_thread:
                            cur_poller_log = cur_poller_log + temp_log
                    elif self.full_log[line_index_iter].startswith('<![LOG'):
                        # if cur_poller_thread == locate_thread(self.full_log[line_index_iter]):
                        # normal log line with same thread id
                        """
                        Fixing for UWP app have multiple threads logs in one app poller
                        """
                        cur_poller_log = cur_poller_log + self.full_log[line_index_iter]

                    line_index_iter = line_index_iter + 1
                application_poller_logs.append(cur_poller_log)

        return application_poller_logs, application_poller_threads

    def initialize_app_poller_object_list(self):
        app_poller_log_list, app_poller_thread_list = self.initialize_app_poller_list()
        self.poller_num = len(app_poller_log_list)
        for index_app_poller_log in range(self.poller_num):
            self.app_poller_object_list.append(ApplicationPoller(app_poller_log_list[index_app_poller_log],
                                                                 app_poller_thread_list[index_app_poller_log]))

    def generate_ems_lifecycle_log_output(self, show_not_expired_subgraph):
        interpreted_log_output = ""
        for cur_app_poller_log_index in range(self.poller_num):
            cur_app_poller_log = self.app_poller_object_list[cur_app_poller_log_index]
            ems_lifecycle_log_output = cur_app_poller_log.generate_application_poller_log_output(show_not_expired_subgraph)
            if ems_lifecycle_log_output != "":
                interpreted_log_output += ems_lifecycle_log_output
                interpreted_log_output += '\n'
        return interpreted_log_output
