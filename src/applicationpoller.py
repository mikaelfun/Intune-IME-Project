"""
This is Class def for Application Poller.
Each EMS lifecycle may contain multiple Application Poller sessions due to scheduled check-ins
Create this class object for each Application Poller.

Error Code range: 3000 - 3999

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
import usersession


class ApplicationPoller:
    def __init__(self, app_poller_log, app_poller_thread_string):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.log_content = list(app_poller_log.split("\n"))
        if self.log_content[-1] == "":
            self.log_content.pop(-1)
        self.log_len = len(self.log_content)
        if self.log_len < 3 or len(self.log_content[0]) < 9:
            print("Error self.log_len < 3! Exit 3100")
            return
            # exit(3101)
        self.app_poller_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])[:-4]
        self.thread_id = app_poller_thread_string
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])
        self.stop_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[-1])
        # self.app_processing_line_start, self.app_processing_line_stop = self.get_each_app_processing_lines()
        # self.number_of_apps_processed = len(self.app_processing_line_start)
        """
        2025-01-22
        Fix bug where multiple AAD users logged in, there will be multi-session check-ins inside 1 App poller
        
        <![LOG[[Win32App] Total valid AAD User session count is 0/1/2/3]
        
        0 means userless session, will pickup device targeting apps.
        1 means 1 logged on aad user, will pickup device+user targeting apps.
        2 means 2 logged on aad user, will pickup device+user1 in user session 1, device+user2 in user session 2 
        """
        self.is_userless_session = False
        self.has_expired_session = False
        self.user_session_num = 0
        self.is_throttled = False
        # If there is any logged on user, session list is composed of each user session. If no logged on user, session list is single device session
        self.session_list = []

        self.index_list_user_session_processing_start = []
        self.index_list_user_session_processing_stop = []

        self.init_app_poller_meta_data()
        """
        2025.1.22 Fix bug where AppWorkload log gets flushed, app poller missing start and missing policy json. This app poller needs to be dumped
        """
        if not self.is_throttled: # and self.get_policy_json:
            self.initialize_session_list()

    def init_app_poller_meta_data(self):
        for log_line_index in range(self.log_len):
            each_line = self.log_content[log_line_index]
            if logprocessinglibrary.locate_thread(each_line) != self.thread_id:
                # ignoring log not belonging to this poller thread. All these metadata are not related to UWP special case with new thread ID on installing.
                continue
            """
            <![LOG[[Win32App] Got 0/1/2/.. active user sessions]LOG]
            """
            if each_line.startswith(self.log_keyword_table['LOG_USER_SESSION_NUM_1']) and self.log_keyword_table['LOG_USER_SESSION_NUM_2'] in each_line:  # get number of user sessions
                end_place = each_line.find(self.log_keyword_table['LOG_USER_SESSION_NUM_2'])
                self.user_session_num = int(each_line[len(self.log_keyword_table['LOG_USER_SESSION_NUM_1']):end_place])

                if self.user_session_num == 0:
                    self.is_userless_session = True

    def initialize_session_list(self):
        """
        <![LOG[[Win32App] ----------------------------------------------------- application poller starts. ----------------------------------------------------- ]LOG]!><time="07:18:23.2001775" date="9-27-2024" component="AppWorkload" context="" type="2" thread="26" file="">
        <![LOG[[Win32App] Got 2 active user sessions]LOG]!><time="07:18:23.3489345" date="9-27-2024" component="AppWorkload" context="" type="1" thread="26" file="">
        <![LOG[[Win32App] ..................... Processing user session 1, userId: 81a25b05-0a31-42cc-93d8-d9e462961f61, userSID:  ..................... ]LOG]!><time="07:18:23.4430143" date="9-27-2024" component="AppWorkload" context="" type="2" thread="26" file="">
         <![LOG[[Win32App][V3Processor] Done processing 4 subgraphs.]LOG]!><time="07:18:24.2914236" date="9-27-2024" component="AppWorkload" context="" type="1" thread="26" file="">
        <![LOG[[Win32App] ..................... Completed user session 1, userId: 81a25b05-0a31-42cc-93d8-d9e462961f61, userSID: S-1-5-21-3222387202-2936485571-3282210269-119131 ..................... ]LOG]!><time="07:18:24.2914236" date="9-27-2024" component="AppWorkload" context="" type="2" thread="26" file="">
        <![LOG[[Win32App] ..................... Processing user session 2, userId: ca5f3999-bd54-474d-9ca3-61f3568c0a6d, userSID:  ..................... ]LOG]!><time="07:18:24.2914236" date="9-27-2024" component="AppWorkload" context="" type="2" thread="26" file="">
        <![LOG[[Win32App] ..................... Completed user session 2, userId: ca5f3999-bd54-474d-9ca3-61f3568c0a6d, userSID: S-1-5-21-3222387202-2936485571-3282210269-119133 ..................... ]LOG]!><time="07:19:51.8605774" date="9-27-2024" component="AppWorkload" context="" type="2" thread="26" file="">
        <![LOG[[Win32App] ----------------------------------------------------- application poller stopped. ----------------------------------------------------- ]LOG]!><time="07:19:51.8758800" date="9-27-2024" component="AppWorkload" context="" type="2" thread="26" file="">
        """
        temp_index_list_user_session_processing_start, temp_index_list_user_session_processing_stop = [], []
        for log_line_index in range(self.log_len):
            cur_line = self.log_content[log_line_index]
            """
            Fix bug that will read other threads app processing.
            """
            if logprocessinglibrary.locate_thread(cur_line) != self.thread_id:
                continue
            if cur_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_START_INDICATOR']):
                temp_index_list_user_session_processing_start.append(log_line_index)
            elif cur_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_STOP_INDICATOR']):
                temp_index_list_user_session_processing_stop.append(log_line_index)
            elif cur_line.startswith(self.log_keyword_table['LOG_USER_SESSION_PROCESS_STOP_2_INDICATOR']):
                temp_index_list_user_session_processing_stop.append(log_line_index)
            elif (self.log_keyword_table['LOG_USER_SESSION_PROCESS_INTERRUPTED_BY_REBOOT_INDICATOR']) in cur_line:
                temp_index_list_user_session_processing_stop.append(log_line_index)

        if len(temp_index_list_user_session_processing_start) == len(temp_index_list_user_session_processing_stop) + 1:
            temp_index_list_user_session_processing_stop.append(self.log_len - 1)
        self.index_list_user_session_processing_start, self.index_list_user_session_processing_stop = (
            logprocessinglibrary.align_index_lists(temp_index_list_user_session_processing_start, temp_index_list_user_session_processing_stop))

        if len(self.index_list_user_session_processing_start) == 0 or len(self.index_list_user_session_processing_stop) == 0:
            #print("Warning No valid user session in this poller! Exit 3000. app poller time stamp: " + self.app_poller_time)
            """
            <![LOG[[Win32App] Skipping available check-in. This is a session log-on-initiated available sync and there are no logged-on users that are in the available check-in schedule.]LOG]!><time="13:08:41.7626010" date="1-21-2025" component="AppWorkload" context="" type="1" thread="28" file="">
            """
            return None

        if self.is_userless_session:
            """
            <![LOG[[Win32App] ..................... Processing user session 0, userId: 00000000-0000-0000-0000-000000000000, userSID:  ..................... ]LOG]!><time="13:05:48.8261848" date="1-21-2025" component="AppWorkload" context="" type="2" thread="15" file="">
            <![LOG[Comgt app workload status False]LOG]!><time="13:05:48.8720251" date="1-21-2025" component="IntuneManagementExtension" context="" type="1" thread="15" file="">
            <![LOG[[Win32App] The EspPhase: NotInEsp in session]LOG]!><time="13:05:48.9834233" date="1-21-2025" component="AppWorkload" context="" type="2" thread="15" file="">
            <![LOG[[Win32App] Requesting required apps]LOG]!><time="13:05:48.9834233" date="1-21-2025" component="AppWorkload" context="" type="2" thread="15" file="">
            <![LOG[[Win32App] Got 6 Win32App(s) for user 00000000-0000-0000-0000-000000000000 in session 0]LOG]!><time="13:05:49.6188306" date="1-21-2025" component="AppWorkload" context="" type="1" thread="15" file="">
            <![LOG[[Win32App][V3Processor] Processing 6 subgraphs.]LOG]!><time="13:05:49.6608904" date="1-21-2025" component="AppWorkload" context="" type="1" thread="15" file="">

            <![LOG[[Win32App][V3Processor] Done processing 6 subgraphs.]LOG]!><time="13:06:16.7660637" date="1-21-2025" component="AppWorkload" context="" type="1" thread="15" file="">
            <![LOG[[Win32App] ..................... Completed user session 0, userId: 00000000-0000-0000-0000-000000000000, userSID:  ..................... ]LOG]!><time="13:06:16.7819559" date="1-21-2025" component="AppWorkload" context="" type="2" thread="15" file="">
            """
            # Only 1 userless session present
            self.user_session_num = 1
            log_start_index = self.index_list_user_session_processing_start[0]
            log_stop_index = self.index_list_user_session_processing_stop[0] + 1
            device_session_log = self.log_content[log_start_index: log_stop_index]
            device_session = usersession.UserSession(device_session_log, self.thread_id)
            self.session_list.append(device_session)
            if device_session.has_expired_subgraph:
                self.has_expired_session = True

        else:
            """
            <![LOG[[Win32App] ----------------------------------------------------- application poller starts. ----------------------------------------------------- ]LOG]!><time="14:59:27.6087227" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">

            <![LOG[[Win32App] ..................... Processing user session 2, userId: 76ab029d-1395-4203-a72b-a716d6117f91, userSID: S-1-12-1-1990918813-1107497877-380054439-2441023958 ..................... ]LOG]!><time="14:59:31.1487327" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">
            <![LOG[[Win32App][V3Processor] Done processing 87 subgraphs.]LOG]!><time="15:03:17.5857511" date="1-20-2025" component="AppWorkload" context="" type="1" thread="52" file="">
            <![LOG[[Win32App] ..................... Completed user session 2, userId: 76ab029d-1395-4203-a72b-a716d6117f91, userSID: S-1-12-1-1990918813-1107497877-380054439-2441023958 ..................... ]LOG]!><time="15:03:17.5857511" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">

            <![LOG[[Win32App] ..................... Processing user session 3, userId: a7d5b8e6-8b43-45e8-b9e9-d9dfe4489228, userSID: S-1-12-1-2815801574-1172867907-3755600313-680675556 ..................... ]LOG]!><time="15:03:17.5857511" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">
            <![LOG[[Win32App][V3Processor] Done processing 84 subgraphs.]LOG]!><time="15:07:50.5243809" date="1-20-2025" component="AppWorkload" context="" type="1" thread="52" file="">
            <![LOG[[Win32App] ..................... Completed user session 3, userId: a7d5b8e6-8b43-45e8-b9e9-d9dfe4489228, userSID: S-1-12-1-2815801574-1172867907-3755600313-680675556 ..................... ]LOG]!><time="15:07:50.5243809" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">
            
            <![LOG[[Win32App] ----------------------------------------------------- application poller stopped. ----------------------------------------------------- ]LOG]!><time="15:07:50.7743804" date="1-20-2025" component="AppWorkload" context="" type="2" thread="52" file="">
            """
            self.user_session_num = len(self.index_list_user_session_processing_start)
            for each_session_index in range(self.user_session_num):
                cur_session_start = self.index_list_user_session_processing_start[each_session_index]
                cur_session_stop = self.index_list_user_session_processing_stop[each_session_index] + 1
                cur_session_log = self.log_content[cur_session_start: cur_session_stop]
                cur_user_session = usersession.UserSession(cur_session_log, self.thread_id)
                self.session_list.append(cur_user_session)
                if cur_user_session.has_expired_subgraph:
                    self.has_expired_session = True

    def generate_application_poller_log_output(self, show_full_log):
        interpreted_log_output = ""
        if not show_full_log:
            if len(self.session_list) == 0:
                # no valid user session
                return interpreted_log_output
            elif not self.has_expired_session:
                return interpreted_log_output
        else:
            pass

        first_line = self.log_content[0]
        if first_line.startswith(
                self.log_keyword_table['LOG_APP_POLLER_START_STRING']):
            interpreted_log_output += constructinterpretedlog.write_application_poller_start_to_log_output(
                "Application Poller Starts",
                self.user_session_num, self.app_poller_time)
        else:
            interpreted_log_output += constructinterpretedlog.write_application_poller_start_to_log_output(
                "Application Poller Missing Start",
                self.user_session_num, self.app_poller_time)

        interpreted_log_output += "\n"

        if show_full_log and len(self.session_list) == 0:
            # no valid user session
            interpreted_log_output += "No valid user session inside this Application Poller. Skipping"
            interpreted_log_output += "\n\n"

        for each_session in self.session_list:
            interpreted_log_output += each_session.generate_user_session_log_output(show_full_log)

        # interpreted_log_output += "\n"
        last_line = self.log_content[-1]
        if last_line.startswith(self.log_keyword_table['LOG_APP_POLLER_STOP_STRING']):
            interpreted_log_output += constructinterpretedlog.write_empty_dash_to_log_output()
            interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('Application Poller Stops')
            interpreted_log_output += constructinterpretedlog.write_empty_dash_to_log_output()
        else:
            interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('Application Poller Missing Stop')
            interpreted_log_output += constructinterpretedlog.write_string_in_middle_with_dash_to_log_output('log may be incomplete')

        return interpreted_log_output