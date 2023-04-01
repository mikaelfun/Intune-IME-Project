

import os
import datetime
CONST_APP_ID_LEN = 36
CONST_GRS_HASH_KEY_LEN = 44
CONST_LOGGING_LENGTH = 190
CONST_META_VALUE_INDEX = 30
CONST_META_DEPENDENT_APP_VALUE_INDEX = 32


def get_timestamp_by_line(log_line):
    # datetime in log looks like <time="09:11:50.3993219" date="3-12-2021" component="
    time_index = log_line.find("time=") + 6
    date_index = log_line.find("date=") + 6
    component_index = log_line.find("component=")
    line_date = log_line[date_index:component_index - 2]
    line_time = log_line[time_index:date_index - 12]

    return line_date + " " + line_time


def convert_date_string_to_date_time(date_string):
    return datetime.datetime.strptime(date_string, '%m-%d-%Y %H:%M:%S')


def locate_thread(line):
    thread_index = line.find('thread="') + 8
    thread_index_end = line.find('" file=')
    if thread_index > thread_index_end or thread_index_end == -1:
        return "-1"
    else:
        return line[thread_index:thread_index_end]


def locate_line_startswith_keyword(full_log, keyword):
    line_index_list = []
    for index in range(len(full_log)):
        if full_log[index].startswith(keyword):
            line_index_list.append(index)
    return line_index_list


def locate_line_contains_keyword(full_log, keyword):
    line_index_list = []
    for index in range(len(full_log)):
        if keyword in full_log[index]:
            line_index_list.append(index)
    return line_index_list


def process_breaking_line_log(full_log):
    """
    <![LOG[AAD User check is failed, exception is System.ComponentModel.Win32Exception (0x80004005):
    An attempt was made to reference a token that does not exist
    at Microsoft.Management.Services.IntuneWindowsAgent.AgentCommon.ImpersonateHelper.<DoActionWithImpersonation>d__4.
    MoveNext()

    or

    <![LOG[[Win32App][WinGetApp][WinGetAppDetectionExecutor] Completed detection for app with id:
    9c393ca7-92fc-4e9e-94d0-f8e303734f7b.
    WinGet operation result:

    """
    log_len = len(full_log)
    line_index_iter = 0
    temp_log = full_log[line_index_iter].replace('\n', ' | ')
    line_index_iter = line_index_iter + 1
    while line_index_iter < log_len and "-1" == locate_thread(full_log[line_index_iter]):
        temp_log = temp_log + full_log[line_index_iter].replace('\n', ' | ')
        line_index_iter = line_index_iter + 1
    if line_index_iter < log_len:
        '''last line

        Error code: ]LOG]!><time="11:41:35.9474014" date="3-23-2023" 
        component="IntuneManagementExtension" context="" type="1" thread="22" file="">

        or

        at Microsoft.Management.Services.IntuneWindowsAgent.AgentCommon.
        DiscoveryService.<IsAADUserInternal>d__17.MoveNext(), session is 1]LOG]!>
        <time="12:37:52.0636654" date="3-23-2023" 
        component="IntuneManagementExtension" context="" type="1" thread="5" file="">
        '''
        temp_log = temp_log + full_log[line_index_iter]
        return temp_log
    else:
        return ""

