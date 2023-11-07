from logprocessinglibrary import *

"""
Output standards:
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++Device Reboots++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++IME Service Starts+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++IME Service Restarts++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++



-----------------------------------------------------------------------------------------------------------------------------------------
---------------------------------------------------------IME Service Missing Start-------------------------------------------------------
-----------------------------------------------------------log may be incomplete---------------------------------------------------------




---------------------------------------------------------Application Poller Stops--------------------------------------------------------
-----------------------------------------------------------------------------------------------------------------------------------------



--------------------------------------------------------Application Poller Starts--------------------------------------------------------
-----------------------------------------------------------------------------------------------------------------------------------------
ESP: NotInEsp    Active User: AzureAD\IMEtester        CoMgmt: Intune  App Type: required    App Number: 8  Time: 3-23-2023 14:37:22




------------------------------------------------------Application Poller Missing Stop----------------------------------------------------
-----------------------------------------------------------log may be incomplete---------------------------------------------------------




"""


def write_log_output_line_with_indent_depth(log_line, depth=0):
    return '-' * (depth+1) * 2 + log_line


def write_ime_service_start_by_reason(reason):
    interpreted_log_output = write_empty_plus_to_log_output()
    interpreted_log_output += write_string_in_middle_with_plus_to_log_output(reason)
    interpreted_log_output += write_empty_plus_to_log_output()
    return interpreted_log_output


def write_empty_dash_to_log_output():
    interpreted_log_output = '-' * CONST_LOGGING_LENGTH + '\n'
    return interpreted_log_output


def write_empty_plus_to_log_output():
    interpreted_log_output = '+' * CONST_LOGGING_LENGTH + '\n'
    return interpreted_log_output


def write_string_in_middle_with_dash_to_log_output(mid_string):
    mid_string_len = len(mid_string)
    first_len = (CONST_LOGGING_LENGTH - mid_string_len) // 2
    second_len = CONST_LOGGING_LENGTH - first_len - mid_string_len
    interpreted_log_output = '-' * first_len + mid_string + '-' * second_len + '\n'
    return interpreted_log_output


def write_string_in_middle_with_plus_to_log_output(mid_string):
    mid_string_len = len(mid_string)
    first_len = (CONST_LOGGING_LENGTH - mid_string_len) // 2
    second_len = CONST_LOGGING_LENGTH - first_len - mid_string_len
    interpreted_log_output = '+' * first_len + mid_string + '+' * second_len + '\n'
    return interpreted_log_output


def write_two_string_at_left_and_middle_with_filled_spaces_to_log_output(left_string, mid_string, index=CONST_META_VALUE_INDEX):
    left_string_len = len(left_string)
    first_len = index - left_string_len
    interpreted_log_output = left_string + ' ' * first_len + mid_string + '\n'
    return interpreted_log_output


def write_application_poller_start_to_log_output(mid_string, esp, user, comgmt, app_type, app_num, start_time):
    esp = ('ESP: ' + esp)
    user = ('Active User: ' + user)
    comgmt = ('CoMgmt: ' + comgmt)
    app_type = ('App Type: ' + app_type)
    app_num = ('App Number: ' + app_num)
    start_time = ('Time: ' + start_time)

    esp_len = len(esp)
    user_len = len(user)
    comgmt_len = len(comgmt)
    app_type_len = len(app_type)
    app_num_len = len(app_num)
    start_time_len = len(start_time)

    interval_len = (CONST_LOGGING_LENGTH - esp_len - user_len - comgmt_len - app_type_len - app_num_len - start_time_len) // 5
    last_len = CONST_LOGGING_LENGTH - esp_len - user_len - comgmt_len - app_type_len - app_num_len - start_time_len - interval_len * 4

    interpreted_log_output = write_string_in_middle_with_dash_to_log_output(mid_string)
    if mid_string == "Application Poller Missing Start":
        interpreted_log_output += write_string_in_middle_with_dash_to_log_output("log may be incomplete")
    else:
        interpreted_log_output += write_empty_dash_to_log_output()
    interpreted_log_output += esp
    interpreted_log_output += ' ' * interval_len
    interpreted_log_output += user
    interpreted_log_output += ' ' * interval_len
    interpreted_log_output += comgmt
    interpreted_log_output += ' ' * interval_len
    interpreted_log_output += app_type
    interpreted_log_output += ' ' * interval_len
    interpreted_log_output += app_num
    interpreted_log_output += ' ' * last_len
    interpreted_log_output += start_time
    interpreted_log_output += '\n'

    return interpreted_log_output
