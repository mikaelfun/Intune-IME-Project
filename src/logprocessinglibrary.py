

import os
import datetime
CONST_APP_ID_LEN = 36
CONST_USER_ID_LEN = 36
CONST_GRS_HASH_KEY_LEN = 44
CONST_LOGGING_LENGTH = 190
CONST_META_VALUE_INDEX = 30
CONST_META_DEPENDENT_APP_VALUE_INDEX = 32
LOG_ENDING_STRING = ']LOG]!'
LOG_STARTING_STRING = '<![LOG'
LOG_APP_POLLER_START_STRING = '<![LOG[[Win32App] ----------------------------------------------------- application poller starts.'
LOG_APP_POLLER_STOP_STRING = '<![LOG[[Win32App] ----------------------------------------------------- application poller stopped.'
LOG_V3_PROCESSOR_ALL_SUBGRAPH_1_INDICATOR = '<![LOG[[Win32App][V3Processor] Processing '
LOG_V3_PROCESSOR_ALL_SUBGRAPH_2_INDICATOR = ' subgraphs.]LOG]!'
LOG_REPORTING_STATE_1_INDICATOR = '<![LOG[[Win32App][ReportingManager] App with id: '
LOG_REPORTING_STATE_2_INDICATOR = 'and prior AppAuthority: V3 has been loaded and reporting state initialized'
LOG_REPORTING_STATE_3_INDICATOR = 'could not be loaded from store. Reporting state initialized with initial values. ReportingState: '
LOG_SUBGRAPH_PROCESSING_START_INDICATOR = '<![LOG[[Win32App][V3Processor] Processing subgraph with app ids: '
LOG_SUBGRAPH_PROCESSING_END_INDICATOR = '<![LOG[[Win32App][V3Processor] Done processing subgraph.'
LOG_SUBGRAPH_PROCESSING_NOT_APPLICABLE_INDICATOR = '<![LOG[[Win32App][V3Processor] All apps in the subgraph are not applicable due'

LOG_ESP_INDICATOR = '<![LOG[[Win32App] The EspPhase: '
LOG_USER_INDICATOR = '<![LOG[After impersonation: '
LOG_CO_MA_INDICATOR = '<![LOG[Comgt app workload status '
LOG_APP_MODE_INDICATOR = '<![LOG[[Win32App] Requesting '
LOG_POLLER_APPS_1_INDICATOR = '<![LOG[[Win32App] Got '
LOG_POLLER_APPS_2_INDICATOR = ' Win32App(s) for user'
LOG_THROTTLED_INDICATOR = '<![LOG[Required app check in is throttled.'
LOG_RE_EVAL_INDICATOR = '<![LOG[[Win32App][ReevaluationScheduleManager] Found previous reevaluation check-in time value: '
LOG_SUBGRAPH_RE_EVAL_INDICATOR = '<![LOG[[Win32App][ReevaluationScheduleManager] Found previous subgraph reevaluation time value: '
LOG_SUBGRAPH_NOT_EXPIRED_INDICATOR = '<![LOG[[Win32App][ReevaluationScheduleManager] Subgraph reevaluation interval is not expired'
LOG_POLICY_JSON_INDICATOR = '<![LOG[Get policies = '

LOG_WIN32_GRS_INDICATOR = '<![LOG[[Win32App][GRSManager] Found GRS value: '
LOG_WIN32_NO_GRS_1_INDICATOR = '<![LOG[[Win32App][GRSManager] App with id: '
LOG_WIN32_NO_GRS_2_INDICATOR = "has no recorded GRS value"
LOG_WIN32_APP_PROCESSING_INDICATOR = '<![LOG[[Win32App][ActionProcessor] App with id: '
LOG_WIN32_REPORTING_STATE_INDICATOR = '<![LOG[[Win32App][ReportingManager] Sending status to company portal based on report: {"ApplicationId":"'
LOG_WIN32_DOWNLOADING_INDICATOR = '<![LOG[[StatusService] Downloading app (id = '
LOG_WIN32_EXECUTING_1_INDICATOR = '<![LOG[[Win32App] ===Step=== Execute retry'
LOG_UWP_EXECUTING_INDICATOR = '<![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Completed execution for app with id: '
LOG_UWP_PROCMON_EXECUTING_INDICATOR = '<![LOG[[ProcessMonitor] Calling CreateProcessAsUser:'
LOG_UWP_START_EXECUTING_INDICATOR = '<![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Starting execution of app with id: '
LOG_UWP_FINISH_EXECUTING_INDICATOR = '<![LOG[[Win32App][WinGetApp][WinGetAppExecutionExecutor] Completed execution for app with id: '
LOG_UWP_FINISH_DETECTION_INDICATOR = '<![LOG[[Win32App][WinGetApp][WinGetAppDetectionExecutor] Completed detection for app with id: '



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
