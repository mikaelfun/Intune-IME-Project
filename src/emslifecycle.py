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
import logprocessinglibrary
import applicationpoller


class EMSLifeCycle:
    def __init__(self, full_log, boot_reason="IME Service Starts"):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
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
        line_index_start_list = logprocessinglibrary.locate_line_startswith_keyword(self.full_log, self.log_keyword_table['LOG_APP_POLLER_START_STRING'])
        line_index_stop_list = logprocessinglibrary.locate_line_startswith_keyword(self.full_log, self.log_keyword_table['LOG_APP_POLLER_STOP_STRING'])

        '''
        Consecutive start stop should have same thread ID. Dropping if thread ID is not match
         <![LOG[[Win32App] ----------------------------------------------------- application poller starts. ----------------------------------------------------- ]LOG]!><time="07:04:15.4880472" date="3-25-2023" component="IntuneManagementExtension" context="" type="2" thread="47" file="">
	     <![LOG[[Win32App] ----------------------------------------------------- application poller stopped. ----------------------------------------------------- ]LOG]!><time="12:04:17.0435845" date="3-25-2023" component="IntuneManagementExtension" context="" type="2" thread="47" file="">
        '''

        while len(line_index_start_list) != 0 and len(line_index_stop_list) != 0:
            cur_start_index = line_index_start_list.pop(0)
            cur_poller_thread = logprocessinglibrary.locate_thread(self.full_log[cur_start_index])
            cur_poller_log = self.full_log[cur_start_index]
            application_poller_threads.append(cur_poller_thread)

            line_index_iter = cur_start_index + 1
            while line_index_iter < self.log_len:
                if line_index_iter in line_index_stop_list and cur_poller_thread == logprocessinglibrary.locate_thread(
                        self.full_log[line_index_iter]):
                    # finds first poller stop line and thread id matches
                    cur_poller_log = cur_poller_log + self.full_log[line_index_iter]
                    application_poller_logs.append(cur_poller_log)
                    line_index_stop_list.remove(line_index_iter)
                    break
                elif self.full_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']) and "-1" == logprocessinglibrary.locate_thread(
                        self.full_log[line_index_iter]):
                    # breaking log start line
                    """
                    eg.
                    <![LOG[[Win32App][ActionProcessor] App with id: 4f0de38e-fe59-4ebf-8660-b2e3bd57bb09, effective intent: RequiredInstall, and enforceability: Enforceable has projected enforcement classification: EnforcementPoint with desired state: Present. Current state is:
                    Detection = NotDetected
                    Applicability =  Applicable
                    Reboot = Clean
                    Local start time = 1/1/0001 12:00:00 AM
                    Local deadline time = 1/1/0001 12:00:00 AM
                    GRS expired = True]LOG]!><time="12:50:53.0788084" date="2-27-2023" component="IntuneManagementExtension" context="" type="1" thread="14" file="">
                    <![LOG[[Win32App][ActionProcessor] Found: 0 apps with intent to uninstall before enforcing installs: [].]LOG]!><time="12:50:53.0788084" date="2-27-2023" component="IntuneManagementExtension" context="" type="1" thread="14" file="">
                    """
                    temp_log = logprocessinglibrary.process_breaking_line_log(self.full_log[line_index_iter:])
                    if temp_log != "" and logprocessinglibrary.locate_thread(temp_log) == cur_poller_thread:
                        cur_poller_log = cur_poller_log + temp_log
                    line_index_iter = line_index_iter + temp_log.count(' | ') + 1
                elif self.full_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']):
                    """
                    Fixing for UWP app have multiple threads logs in one app poller
                    """
                    thread_id_exception_headers = self.log_keyword_table['LOG_MSFB_THREAD_ID_EXCEPTION_HEADERS']
                    is_msfb_second_thread = False
                    for each_header in thread_id_exception_headers:
                        if self.full_log[line_index_iter].startswith(each_header):
                            is_msfb_second_thread = True
                    if cur_poller_thread == logprocessinglibrary.locate_thread(self.full_log[line_index_iter]) or is_msfb_second_thread:
                        # normal log line with same thread id
                        cur_poller_log = cur_poller_log + self.full_log[line_index_iter]

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
                cur_poller_thread = logprocessinglibrary.locate_thread(self.full_log[each_start_index])
                application_poller_threads.append(cur_poller_thread)
                cur_poller_log = self.full_log[each_start_index]
                line_index_iter = each_start_index
                while line_index_iter < self.log_len:
                    if self.full_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']) and "-1" == logprocessinglibrary.locate_thread(
                            self.full_log[line_index_iter]):
                        # beginning of line breaking logs
                        temp_log = logprocessinglibrary.process_breaking_line_log(self.full_log[line_index_iter:])

                        if temp_log != "" and logprocessinglibrary.locate_thread(temp_log) == cur_poller_thread:
                            cur_poller_log = cur_poller_log + temp_log
                        line_index_iter = line_index_iter + temp_log.count(' | ') + 1
                    elif self.full_log[line_index_iter].startswith(self.log_keyword_table['LOG_STARTING_STRING']):
                        """
                        Fixing for UWP app have multiple threads logs in one app poller
                        """
                        thread_id_exception_headers = self.log_keyword_table['LOG_MSFB_THREAD_ID_EXCEPTION_HEADERS']
                        is_msfb_second_thread = False
                        for each_header in thread_id_exception_headers:
                            if self.full_log[line_index_iter].startswith(each_header):
                                is_msfb_second_thread = True
                        if cur_poller_thread == logprocessinglibrary.locate_thread(
                                self.full_log[line_index_iter]) or is_msfb_second_thread:
                            # normal log line with same thread id
                            cur_poller_log = cur_poller_log + self.full_log[line_index_iter]

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

    def generate_ems_lifecycle_log_output(self, show_not_expired_subgraph):
        interpreted_log_output = ""
        for cur_app_poller_log_index in range(self.poller_num):
            cur_app_poller_log = self.app_poller_object_list[cur_app_poller_log_index]
            ems_lifecycle_log_output = cur_app_poller_log.generate_application_poller_log_output(show_not_expired_subgraph)
            if ems_lifecycle_log_output != "":
                interpreted_log_output += ems_lifecycle_log_output
                interpreted_log_output += '\n'
        return interpreted_log_output
