# break logs into lines and return list of lines as loaded logs
# IME log are mixed with multiple threads
# It is important to separate logs into each thread processing
from Win32_log_processing import *


def locate_thread(line):
    thread_index = line.find('thread="') + 8
    thread_index_end = line.find('" file=')
    return line[thread_index:thread_index_end]


def get_timestamp_by_line(log_line):
    # datetime in log looks like <time="09:11:50.3993219" date="3-12-2021" component="
    time_index = log_line.find("time=") + 6
    date_index = log_line.find("date=") + 6
    component_index = log_line.find("component=")
    line_date = log_line[date_index:component_index - 2]
    line_time = log_line[time_index:date_index - 8]

    return line_date + " " + line_time


def locate_line_startswith_keyword(win32_app_log, keyword):
    for index in range(len(win32_app_log)):
        if win32_app_log[index].startswith(keyword):
            return index
    return -1


def locate_line_startswith_keyword_backward(win32_app_log, keyword):
    loglen = len(win32_app_log)
    for index in range(len(win32_app_log)):
        if win32_app_log[loglen - 1 - index].startswith(keyword):
            return loglen - 1 - index
    return -1

def locate_line_contains_keyword(win32_app_log, keyword):
    for index in range(len(win32_app_log)):
        if keyword in win32_app_log[index]:
            return index
    return -1


class Win32AppPollerLog:
    def __init__(self, source_log, thread_string):  # input is log content
        self.log_content = []
        for log_line_index in range(len(source_log)):
            line_thread = locate_thread(source_log[log_line_index])
            if thread_string == line_thread:
                self.log_content.append(source_log[log_line_index])
            if source_log[log_line_index].startswith('<![LOG[EMS Agent Started]LOG]'):
                self.log_content.append(source_log[log_line_index])

        self.thread_id = thread_string
        self.length = len(self.log_content)
        self.start_time = get_timestamp_by_line(source_log[0])
        self.stop_time = get_timestamp_by_line(source_log[-1])
        self.app_processing_line_start, self.app_processing_line_stop = self.get_each_app_processing_lines()
        self.number_of_apps_processed = 0
        self.number_of_apps_processed = len(self.app_processing_line_start)
        self.esp_phase = ""
        self.user_session = ""
        self.poller_apps_got = ""
        self.poller_apps_got_filtered = ""
        self.comanagement_workload = ""
        self.apptype = ""
        self.get_poller_meta_data()

    def get_poller_meta_data(self):
        for log_line_index in range(self.length):
            eachline = self.log_content[log_line_index]
            if not self.esp_phase and eachline.startswith('<![LOG[[Win32App] The EspPhase:'):  # get ESP phase
                endplace = eachline.find(".]LOG]!")
                self.esp_phase = eachline[32:endplace]
                '''
                <![LOG[[Win32App] The EspPhase: NotInEsp.]LOG]!
                <![LOG[[Win32App] The EspPhase: DevicePreparation.]LOG]!
                <![LOG[[Win32App] The EspPhase: DeviceSetup.]LOG]!
                <![LOG[[Win32App] The EspPhase: AccountSetup.]LOG]!
                '''
            elif not self.user_session and eachline.startswith('<![LOG[After impersonation:'):  # get current user session
                endplace = eachline.find("]LOG]!")
                self.user_session = eachline[28:endplace]
            elif not self.comanagement_workload and eachline.startswith('<![LOG[Comgt app workload status '):
                endplace = eachline.find("]LOG]!")
                if eachline[33:endplace] == "False":
                    self.comanagement_workload = "Intune"
                elif eachline[33:endplace] == "True":
                    self.comanagement_workload = "SCCM"
                else:
                    self.comanagement_workload = "Unknown"
            elif not self.apptype and eachline.startswith('<![LOG[[Win32App] Requesting ') and ('apps only]' in eachline or 'for ESP]' in eachline):
                endplace = 29
                if eachline.find(" apps only]LOG]!") > 0:
                    endplace = eachline.find(" apps only]LOG]!")
                elif eachline.find(" for ESP]") > 0:
                    endplace = eachline.find(" for ESP]")
                self.apptype = eachline[29:endplace]
            elif not self.poller_apps_got and eachline.startswith('<![LOG[[Win32App] Got ') and 'Win32App(s) for user' in eachline:
                endplace = eachline.find(" Win32App(s) for user")
                self.poller_apps_got = eachline[22:endplace]
            elif not self.poller_apps_got_filtered and eachline.startswith('<![LOG[[Win32App]  Get ') and ' win32 apps after filtering' in eachline:
                endplace = eachline.find(" win32 apps after filtering")
                self.poller_apps_got_filtered = eachline[23:endplace]

    def get_each_app_processing_lines(self):
        app_processing_line_start = []
        app_processing_line_stop = []
        for log_line_index in range(self.length):
            eachline = self.log_content[log_line_index]
            '''
            App with dependency auto install:
            
            <![LOG[[Win32App] ExecManager: processing targeted app (name='Copy Json v3', id='48054978-39bd-40da-8d45-0d28004b4960') with intent=3, appApplicabilityStateDueToAssginmentFilters= for user session 0]LOG]!><time="15:32:57.0285627" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[[Win32App] ProcessAppWithDependencies starts for 48054978-39bd-40da-8d45-0d28004b4960 with name Copy Json v3]LOG]!><time="15:32:57.0285627" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            
            <![LOG[[Win32App] Completed detectionManager SideCarFileDetectionManager, applicationDetectedByCurrentRule: False]LOG]!><time="15:32:57.0375387" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[[Win32App] starts processing the app chain for app 48054978-39bd-40da-8d45-0d28004b4960, name = Copy Json v3]LOG]!><time="15:32:57.0375387" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[[Win32App] Aggregated result for (9e309cc3-fc69-4906-a73b-c692aec58fa5,Cisco AnyConnect Secure Mobility Client - 4.10) is Success]LOG]!><time="15:32:57.0534964" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[---->>[Win32App] Processing app (id=9e309cc3-fc69-4906-a73b-c692aec58fa5, name = Cisco AnyConnect Secure Mobility Client - 4.10) with mode = DetectInstall]LOG]!><time="15:32:57.0544943" date="11-11-2021" component="IntuneManagementExtension" context="" type="2" thread="5" file="">
                        
            <![LOG[[Win32App] added new report for 9e309cc3-fc69-4906-a73b-c692aec58fa5, Cisco AnyConnect Secure Mobility Client - 4.10]LOG]!><time="15:33:34.3799461" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[[Win32App] Aggregated result for (6b563018-53fa-4857-9156-cfb0ba1e87da,Cisco AnyConnect Umbrella Roaming Security Module - 4.10) is Success]LOG]!><time="15:33:34.3839452" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[---->>[Win32App] Processing app (id=6b563018-53fa-4857-9156-cfb0ba1e87da, name = Cisco AnyConnect Umbrella Roaming Security Module - 4.10) with mode = DetectInstall]LOG]!><time="15:33:34.3839452" date="11-11-2021" component="IntuneManagementExtension" context="" type="2" thread="5" file="">
            <![LOG[----[Win32App] app with name = Cisco AnyConnect Umbrella Roaming Security Module - 4.10 dependency detect only is False]LOG]!><time="15:33:34.3839452" date="11-11-2021" component="IntuneManagementExtension" context="" type="2" thread="5" file="">
            <![LOG[[Win32App] ===Step=== Start to Present app 6b563018-53fa-4857-9156-cfb0ba1e87da]LOG]!><time="15:33:34.3839452" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            
            <![LOG[[Win32App] added new report for 6b563018-53fa-4857-9156-cfb0ba1e87da, Cisco AnyConnect Umbrella Roaming Security Module - 4.10]LOG]!><time="15:34:02.9804236" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">
            <![LOG[---->>[Win32App] Processing app (id=48054978-39bd-40da-8d45-0d28004b4960, name = Copy Json v3) with mode = DetectInstall]LOG]!><time="15:34:02.9804236" date="11-11-2021" component="IntuneManagementExtension" context="" type="2" thread="5" file="">
            <![LOG[----[Win32App] app with name = Copy Json v3 dependency detect only is False]LOG]!><time="15:34:02.9804236" date="11-11-2021" component="IntuneManagementExtension" context="" type="2" thread="5" file="">
            <![LOG[[Win32App] ===Step=== Start to Present app 48054978-39bd-40da-8d45-0d28004b4960]LOG]!><time="15:34:02.9804236" date="11-11-2021" component="IntuneManagementExtension" context="" type="1" thread="5" file="">

'''
            if eachline.startswith('<![LOG[[Win32App] ExecManager: processing targeted app'):
                start_place = eachline.find("id='")
                end_place = eachline.find("') with intent")
                app_id = eachline[start_place + 4: end_place]
                search_string = "<![LOG[[Win32App] app result (id = " + app_id
                app_result_line = locate_line_startswith_keyword(self.log_content[log_line_index:], search_string)
                app_stop_line = app_result_line  + log_line_index
                if app_result_line > 0:
                    app_processing_line_start.append(log_line_index)
                    app_processing_line_stop.append(app_stop_line + 1)
                else: #add incomplete app log
                    app_processing_line_start.append(log_line_index)
                    app_processing_line_stop.append(self.length)

        return app_processing_line_start, app_processing_line_stop


class IMELog:
    def __init__(self, IME_log_path):
        self.full_log = self.load_IME_log(IME_log_path)
        self.win32_poller_start_index, self.win32_poller_stop_index, self.win32_poller_thread \
            = self.get_Win32_poller_lines(self.full_log)
        self.number_of_poller_sessions = len(self.win32_poller_start_index)
        self.win32_poller_logs_list = self.separate_win32_poller_logs()

    def load_IME_log(self, IME_log_path):
        log_file = open(IME_log_path, encoding='utf-8')
        log_as_lines = log_file.readlines()
        # close file
        log_file.close
        return log_as_lines

    def get_Win32_poller_lines(self, loadedLog):
        """
        :param loadedLog: full log
        :return: 3 lists, of poller start line index, corresponding stop line index, corresponding thread number string.
        """
        win32_poller_lines = []
        win32_poller_stop_lines = []
        poller_start_thread = []
        for i in range(len(loadedLog)):
            if loadedLog[i].startswith(
                    '<![LOG[[Win32App] ----------------------------------------------------- application poller starts.'):
                win32_poller_lines.append(i)
                poller_start_thread.append(locate_thread(loadedLog[i]))

            elif loadedLog[i].startswith(
                    '<![LOG[[Win32App] ----------------------------------------------------- application poller stopped.'):
                if len(win32_poller_stop_lines) <= len(win32_poller_lines) - 1:
                    this_thread = locate_thread(loadedLog[i])
                    if this_thread == poller_start_thread[len(win32_poller_stop_lines)]:
                        win32_poller_stop_lines.append(i)
                    else:
                        while len(win32_poller_stop_lines) <= len(win32_poller_lines) - 1 and \
                                this_thread != poller_start_thread[len(win32_poller_stop_lines)]:
                            win32_poller_lines.pop(len(win32_poller_stop_lines))
                            poller_start_thread.pop(len(win32_poller_stop_lines))
                        if len(win32_poller_stop_lines) >= len(win32_poller_lines):
                            continue
                        if this_thread == poller_start_thread[len(win32_poller_stop_lines)]:
                            win32_poller_stop_lines.append(i)
            elif loadedLog[i].startswith('<![LOG[EMS Agent Started]'): # reboot will let application poller session end prematurely. Add reboot line as end of previous poller if exists
                if len(win32_poller_stop_lines) <= len(win32_poller_lines) - 1:
                    win32_poller_stop_lines.append(i)

        while len(win32_poller_stop_lines) < len(win32_poller_lines) - 1:
            del win32_poller_lines[-1]
            del poller_start_thread[-1]

        if len(win32_poller_stop_lines) == len(win32_poller_lines) - 1:
            win32_poller_stop_lines.append(len(loadedLog) - 1)
        return win32_poller_lines, win32_poller_stop_lines, poller_start_thread

    def separate_win32_poller_logs(self):
        win32_poller_logs_list = []
        for i in range(self.number_of_poller_sessions):
            each_poller_log = Win32AppPollerLog(self.full_log[self.win32_poller_start_index[i]:
                                                              self.win32_poller_stop_index[i]+1],
                                                self.win32_poller_thread[i])
            win32_poller_logs_list.append(each_poller_log)
        return win32_poller_logs_list

    def generate_win32_app_log(self):
        win32_app_log_report = ""
        for each_log in self.win32_poller_logs_list:
            if each_log.number_of_apps_processed > 0:
                #thisdate, thistime = each_log.start_time
                #win32_app_log_report = win32_app_log_report + "Application Poller " + thisdate + " " + thistime + " Starts" + "\n\n"
                win32_app_log_report = win32_app_log_report + "---------------------------------------------------Application Poller Starts-------------------------------------------------------------" + "\n"
                win32_app_log_report = \
                    win32_app_log_report + "++++ESP: " + each_log.esp_phase + "++++Active User: "\
                    +each_log.user_session+"++++CoMgmt: "+each_log.comanagement_workload+"++++App Type: "+\
                    each_log.apptype+"++++Apps Got: "+each_log.poller_apps_got_filtered + "++++\n\n"

                poller_result = self.process_win32_poller(each_log)
                win32_app_log_report = win32_app_log_report + poller_result
                win32_app_log_report = win32_app_log_report + "\n\n"
                #thisdate, thistime = each_log.stop_time
                #win32_app_log_report = win32_app_log_report + "Application Poller " + thisdate + " " + thistime + " Ends"
                # print("debug: " + each_log.log_content[-1])
                if each_log.log_content[-1].startswith('<![LOG[[Win32App] ----------------------------------------------------- application poller stopped.'):
                    win32_app_log_report = win32_app_log_report + "---------------------------------------------------Application Poller Stops-------------------------------------------------------------"
                elif each_log.log_content[-1].startswith('<![LOG[EMS Agent Started]LOG'):
                    win32_app_log_report = win32_app_log_report + "-------------------------------------------------------Device Rebooted------------------------------------------------------------------"
                else:
                    win32_app_log_report = win32_app_log_report + "------------------------------------------------------IME Log Truncated-----------------------------------------------------------------"
                win32_app_log_report = win32_app_log_report + "\n\n\n"
        if win32_app_log_report == "":
            win32_app_log_report = "No App Processing Log found."
        return win32_app_log_report

    def process_win32_poller(self, win32_poller_log):
        output = ""
        # win32_poller_log = Win32AppPollerLog
        for app_processing_index in range(win32_poller_log.number_of_apps_processed):
            result = process_each_app_log(win32_poller_log.log_content[win32_poller_log.app_processing_line_start[app_processing_index]:win32_poller_log.app_processing_line_stop[app_processing_index]])
            if result:
                output += result
                output += "\n"
        return output


def get_powershell_poller_lines(loadedLog):
    powershell_poller_lines = []
    powershell_poller_stop_lines = []
    for i in range(len(loadedLog)):
        if loadedLog[i].startswith('<![LOG[[PowerShell] Polling thread stopped.'):
            if len(powershell_poller_stop_lines) == len(powershell_poller_lines) - 1:
                powershell_poller_stop_lines.append(i+1)
        if loadedLog[i].startswith('<![LOG[[PowerShell] Polling thread starts.]'):
            powershell_poller_lines.append(i)
    return powershell_poller_lines, powershell_poller_stop_lines
