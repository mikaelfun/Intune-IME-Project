import configparser
import os
import datetime
import json

CONST_APP_ID_LEN = 36
CONST_USER_ID_LEN = 36
CONST_GRS_HASH_KEY_LEN = 44
CONST_LOGGING_LENGTH = 0
CONST_META_VALUE_INDEX = 30
CONST_META_DEPENDENT_APP_VALUE_INDEX = 32

try:
    config_local = configparser.ConfigParser()
    config_local.read('config.ini')
    CONST_LOGGING_LENGTH = int(config_local['LOGGINGPRINT']['loglen'])
except:
    print("Error reading config.ini!! Run update.exe to fix!")
    CONST_LOGGING_LENGTH = 134


def init_keyword_table():
    with open('logging keyword table.json', 'r') as f:
        json_table = json.load(f)
        return json_table


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

    log_keyword_table = init_keyword_table()
    log_len = len(full_log)
    line_index_iter = 0
    temp_log = []
    while line_index_iter < log_len:
        # Normal line with start and thread
        if full_log[line_index_iter].startswith(log_keyword_table['LOG_STARTING_STRING']) and "-1" != locate_thread(full_log[line_index_iter]):
            temp_log.append(full_log[line_index_iter])
        elif full_log[line_index_iter].startswith(log_keyword_table['LOG_STARTING_STRING']) and "-1" == locate_thread(full_log[line_index_iter]):
            """
            start of broken log
            <![LOG[AAD User check is failed, exception is System.ComponentModel.Win32Exception (0x80004005):
            """

            temp_log.append(full_log[line_index_iter].replace('\n', ' | '))
        elif not full_log[line_index_iter].startswith(log_keyword_table['LOG_STARTING_STRING']) and "-1" == locate_thread(full_log[line_index_iter]):
            """
            middle of broken log, no start, no thread.
            Append to last line string end.
            """
            temp_log[-1] = temp_log[-1] + full_log[line_index_iter].replace('\n', ' | ')
        elif not full_log[line_index_iter].startswith(log_keyword_table['LOG_STARTING_STRING']) and "-1" != locate_thread(full_log[line_index_iter]):
            """
            end of broken log, no start, got thread.
            Append to last line string end.
            """
            temp_log[-1] = temp_log[-1] + full_log[line_index_iter]

        line_index_iter = line_index_iter + 1

    return temp_log


def find_app_id_with_starting_string(log_line, start_string):
    """
    <![LOG[[Win32App][ActionProcessor] No action required for app with id: b3d77df6-8802-414f-867e-457394d80cca.]LOG]!
    <![LOG[[Win32App][ActionProcessor] App with id: b3d77df6-8802-414f-867e-457394d80cca, effective intent: RequiredInstall

    :param log_line:
    :param start_string:
    :return:
    """
    app_id_index_start = log_line.find(start_string) + len(start_string)
    app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
    cur_app_id = log_line[app_id_index_start:app_id_index_end]
    return cur_app_id
