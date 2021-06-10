# break logs into lines and return list of lines as loaded logs
def load_IME_log(IME_log_path):
    log_file = open(IME_log_path, encoding='utf-8')
    log_as_lines = log_file.readlines()
    # close file
    log_file.close
    return log_as_lines


def get_Win32_poller_lines(loadedLog):
    win32_poller_lines = []
    win32_poller_stop_lines = []
    for i in range(len(loadedLog)):
        if loadedLog[i].startswith('<![LOG[[Win32App] ----------------------------------------------------- application poller stopped.'):
            if len(win32_poller_stop_lines) <= len(win32_poller_lines) - 1:

                win32_poller_stop_lines.append(i+1)
        if loadedLog[i].startswith('<![LOG[[Win32App] ----------------------------------------------------- application poller starts.'):
            win32_poller_lines.append(i)
    if len(win32_poller_stop_lines) < len(win32_poller_lines):
        del win32_poller_lines[-1]
    return win32_poller_lines, win32_poller_stop_lines


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


def get_timestamp_by_line(log_line):
    # datetime in log looks like <time="09:11:50.3993219" date="3-12-2021" component="
    time_index = log_line.find("time=") + 6
    date_index = log_line.find("date=") + 6
    component_index = log_line.find("component=")
    line_date = log_line[date_index:component_index-2]
    line_time = log_line[time_index:date_index-8]
    return line_date, line_time


def locate_line_startswith_keyword(win32_app_log, keyword):
    for index in range(len(win32_app_log)):
        if win32_app_log[index].startswith(keyword):
            return index
    return -1


def locate_line_contains_keyword(win32_app_log, keyword):
    for index in range(len(win32_app_log)):
        if keyword in win32_app_log[index]:
            return index
    return -1


def process_each_app_log(win32_app_log):
    log_output = ""
    if not win32_app_log:
        return log_output
    # i = 0
    current_index = 0
    intent = "REQUIRED INSTALL"
    pre_process_detect = False
    post_process_detect = False
    if not win32_app_log[0].startswith('<![LOG[[Win32App] ExecManager: processing targeted app'):  # exception and stop
        return log_output

    intent_index = win32_app_log[0].find("intent=")
    intent_number = win32_app_log[0][intent_index + 7]
    if intent_number == "4":
        intent = "UNINSTALL"
    elif intent_number == "3":
        intent = "REQUIRED INSTALL"
    elif intent_number == "1":
        intent = "AVAILABLE INSTALL"
    else:
        intent = "UNKNOWN"

    locate_result = locate_line_startswith_keyword(win32_app_log, '<![LOG[---->>[Win32App] Processing app (id=')
    if locate_result < 0:  # exception and stop
        return ""

    # log app name and intent - mandatory
    log_output = log_output + "\n"
    name_index = win32_app_log[locate_result].find("name = ")
    name_index_stop = win32_app_log[locate_result].find(") with mode")
    line_time = get_timestamp_by_line(win32_app_log[locate_result])
    log_output = log_output + line_time[0] + " " + line_time[1] + " Processing app: [" + \
                 win32_app_log[locate_result][name_index + 7:name_index_stop] + "] with intent " + intent
    log_output += '\n'
    current_index = locate_result

    # log pre detection - mandatory
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Detection rules]')
    if locate_result < 0:  # exception and stop
        return ""
    current_index += locate_result

    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Completed detectionManager')
    if locate_result < 0:  # exception and stop
        return ""
    current_index += locate_result
    line_time = get_timestamp_by_line(win32_app_log[current_index])
    start_place = win32_app_log[current_index].find("applicationDetectedByCurrentRule") + 34
    end_place = win32_app_log[current_index].find("]LOG]!")
    if win32_app_log[current_index][start_place:end_place] == "True":
        app_found = "App is installed"
        pre_process_detect = True
    else:
        app_found = "App is NOT installed"
    log_output = log_output + line_time[0] + " " + line_time[1] + " Detect app before processing: " + app_found
    log_output += '\n'

    if intent == "UNINSTALL":
        if not pre_process_detect:
            log_output = log_output + line_time[0] + " " + line_time[
                1] + " Intent is UNINSTALL and app is not detected."
            log_output += '\n'
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Un-installation Result: SUCCESS "
            log_output += '\n'
            return log_output
    elif intent == "REQUIRED INSTALL" or intent == "AVAILABLE INSTALL":
        if pre_process_detect:
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: SUCCESS "
            log_output += '\n'
            return log_output
    else:
        pass

    # log applicability check - mandatory
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Check applicability')
    if locate_result < 0:  # exception and stop
        return ""
    current_index += locate_result
    line_time = get_timestamp_by_line(win32_app_log[current_index])
    if "intent is to un-install, skip applicability check" in win32_app_log[current_index + 1]:
        log_output = log_output + line_time[0] + " " + line_time[
            1] + " Intent is UNINSTALL and app is NOT detected."
        log_output += '\n'
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Un-installation Result: SUCCESS "
        log_output += '\n'
        return log_output
    elif "intent is to install, skip applicability check" in win32_app_log[current_index + 1]:
        log_output = log_output + line_time[0] + " " + line_time[
            1] + " Intent is INSTALL and app is detected."
        log_output += '\n'
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: SUCCESS "
        log_output += '\n'
        return log_output

    # log extended applicability check - optional
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Check Extended requirement rules')
    if locate_result < 0:
        # should be always able to find this line as otherwise it would be returned before
        pass
    else:
        basic_applicability = True
        basic_applicability_reason = ""
        extended_applicability = False
        extended_applicability_reason = ""

        line_time = get_timestamp_by_line(win32_app_log[current_index])

        for applicability_index in range(current_index + 1, current_index + locate_result):
            if "skip check." not in win32_app_log[applicability_index] and \
                    "applicability: Applicable" not in win32_app_log[applicability_index]:
                basic_applicability = False
                end_place = win32_app_log[applicability_index].find("applicability:")
                basic_applicability_reason = win32_app_log[applicability_index][49:end_place - 2]

        if not basic_applicability:
            log_output = log_output + line_time[0] + " " + line_time[
                1] + " Basic Applicability Check: Not Applicable, reason is: " + basic_applicability_reason
            log_output += '\n'
            if intent == "UNINSTALL":
                log_output = log_output + line_time[0] + " " + line_time[
                    1] + " App Un-installation Result: NOT APPLICABLE"
            else:
                log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: NOT APPLICABLE"
            log_output += '\n'
            return log_output
        else:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Basic Applicability Check: Applicable"
            log_output += '\n'
        current_index = current_index + locate_result + 1
        if win32_app_log[current_index].startswith(
                '<![LOG[[Win32App] No ExtendedRequirementRules for this App. Skipping Check Extended requirement rule'):
            extended_applicability = True
        else:

            locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                           '<![LOG[[Win32App] Extended requirement rules processing complete. isApplicationApplicable: ')
            if locate_result < 0:
                # should be always able to find this line as otherwise it would be returned before
                pass
            current_index += locate_result
            if win32_app_log[current_index].startswith('<![LOG[[Win32App] Extended requirement rules processing complete. isApplicationApplicable: Applicable'):
                extended_applicability = True
            else:
                end_place = win32_app_log[current_index].find("]LOG]!")
                extended_applicability_reason = win32_app_log[current_index][91:end_place]

        line_time = get_timestamp_by_line(win32_app_log[current_index])
        if not extended_applicability:
            log_output = log_output + line_time[0] + " " + line_time[
                1] + " Extended Applicability Check: Not Applicable, reason is: " + extended_applicability_reason
            log_output += '\n'
            if intent == "UNINSTALL":
                log_output = log_output + line_time[0] + " " + line_time[
                    1] + " App Un-installation Result: NOT APPLICABLE"
            else:
                log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: NOT APPLICABLE"
            log_output += '\n'
            return log_output
        else:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Extended Applicability Check: Applicable"
            log_output += '\n'

    # log detection without existing AppResult (GRS) - optional
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Check detection without existing AppResult')
    current_index += locate_result
    line_time = get_timestamp_by_line(win32_app_log[current_index])
    if locate_result < 0:
        log_output = log_output + line_time[0] + " " + line_time[1] + " ===Step=== Check detection without existing AppResult MISSING!"
        log_output += '\n'
        return log_output

    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step===')
    if locate_result < 0:
        return ""  # abort this app log

    for grs_index in range(current_index, current_index + locate_result):
        line_time = get_timestamp_by_line(win32_app_log[grs_index])
        if win32_app_log[grs_index].startswith('<![LOG[[Win32App] Tried in last 24 hours, No need to exec. skip execution'):
            log_output = log_output + line_time[0] + " " + line_time[
                1] + " Still in GRS, tried in last 24 hours, skip execution."
            log_output += '\n'
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: SKIP due to GRS"
            log_output += '\n'
            return log_output
        elif win32_app_log[grs_index].startswith('<![LOG[[Win32App] GRS is expired. kick off download & install'):
            log_output = log_output + line_time[0] + " " + line_time[
                1] + " GRS is expired. kick off download & install."
            log_output += '\n'
            break
        else:
            pass

    # log Download - mandatory at this stage, otherwise returned
    # Download will first try with DO, if it fails, it will change to CDN mode and retry immediately.

    #     "<![LOG[Starting job 07944b33-cae1-448a-8153-284246052f5b...]LOG]!><time="19:12:44.0010467" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[...job 07944b33-cae1-448a-8153-284246052f5b started]LOG]!><time="19:12:44.0010467" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[Waiting 43200000 ms for 1 jobs to complete]LOG]!><time="19:12:44.0020431" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[JobError callback (Context: BG_ERROR_CONTEXT_NONE; ErrorCode: 80070005) for job 07944b33-cae1-448a-8153-284246052f5b]LOG]!><time="19:12:51.0228614" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="9" file="">
    # <![LOG[Job has failed. Error: 80070005]LOG]!><time="19:12:54.0030409" date="4-22-2020" component="IntuneManagementExtension" context="" type="3" thread="26" file="">
    # <![LOG[Job 07944b33-cae1-448a-8153-284246052f5b (BG_JOB_STATE_ERROR) failed to complete, cancelling...]LOG]!><time="19:12:54.0040409" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[Exception occurs when downloading content using DO, the file id is 501FCB7D-A970-4E34-A753-4B48FE5D8BEF_21726dda-78ae-4673-9774-ad7a5478b43e_9827a3ed-19ef-4378-b8e3-44b92da6a3d7_bc8f9547-1a4f-4786-a2eb-1f8710b6438c-intunewin-bin_54bea6da-9d3f-4933-968e-6532b0c2a091_1, exception is System.Exception: Do job is in error state, need cancel the job.
    #    at Microsoft.Management.Clients.IntuneManagementExtension.Win32AppPlugIn.ContentManagement.DeliveryOptimization.DOUtilities.WaitForJobsComplete(Tuple`2[] jobs, Int32 totalWaitTime, Int32 timeBetweenPolls)
    #    at Microsoft.Management.Clients.IntuneManagementExtension.Win32AppPlugIn.ContentManagement.DeliveryOptimization.DOUtilities.WaitForJobComplete(IBackgroundCopyJob job, BackgroundCopyCallbackHandler handler, Int32 totalWaitTime, Int32 timeBetweenPolls)
    #    at Microsoft.Management.Clients.IntuneManagementExtension.Win32AppPlugIn.ContentManager.DownloadUsingDeliveryOptimization(Win32AppResult win32AppResult, SideCarApplicationClientPolicy appPolicy, SideCarContentInfo sidecarContentInfo, SideCarContentMetadata contentMetadata, String encryptedFilePath, String downloadFilePath, Boolean& fallback, EspPhase espPhase)]LOG]!><time="19:12:54.0439434" date="4-22-2020" component="IntuneManagementExtension" context="" type="3" thread="26" file="">
    # <![LOG[[StatusService] Unable to get error code and hence returning unknown.]LOG]!><time="19:12:54.0479281" date="4-22-2020" component="IntuneManagementExtension" context="" type="2" thread="26" file="">
    # <![LOG[[StatusService] Returning AppInstallStatus as Unknown since Compliance State is 2.]LOG]!><time="19:12:54.0479281" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[[StatusService] Saved AppInstallStatusReport for user dc36f1fc-eb4d-44c8-9eff-14fe1f533ee5 for app 54bea6da-9d3f-4933-968e-6532b0c2a091 in the StatusServiceReports registry.]LOG]!><time="19:12:54.0479281" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[[StatusService] No subscribers to SendUpdate.]LOG]!><time="19:12:54.0479281" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[[Win32App] CDN mode, content raw URL is http://swdc01.manage.microsoft.com/21726dda-78ae-4673-9774-ad7a5478b43e/9827a3ed-19ef-4378-b8e3-44b92da6a3d7/bc8f9547-1a4f-4786-a2eb-1f8710b6438c.intunewin.bin]LOG]!><time="19:12:54.0479281" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">
    # <![LOG[[Win32App] CDN mode, download completes.]LOG]!><time="19:13:55.3965233" date="4-22-2020" component="IntuneManagementExtension" context="" type="1" thread="26" file="">"

    current_index += locate_result
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Download]LOG]!')
    if locate_result < 0:
        return ""  # abort this app log

    current_index += locate_result
    locate_result_1 = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[Starting job ')
    locate_result_2 = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                    '<![LOG[[StatusService] Downloading app')
    if locate_result_1 < 0 and locate_result_2 < 0:
        return ""  # abort this app log
    elif locate_result_1 >= 0:
        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result_1])
        log_output = log_output + line_time[0] + " " + line_time[1] + " Start downloading app."
        log_output += '\n'

        current_index += locate_result_1

        if locate_line_startswith_keyword(win32_app_log[current_index:], '<![LOG[Job has failed.') >= 0:
            locate_result = locate_line_startswith_keyword(win32_app_log[current_index:], '<![LOG[Job has failed.')
            line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result])
            log_output = log_output + line_time[0] + " " + line_time[1] + " DO Download Job failed. Trying CDN mode."
            log_output += '\n'
            locate_result_3 = locate_line_startswith_keyword(win32_app_log[current_index:], '<![LOG[[Win32App] CDN mode, content raw URL is')
            locate_result_4 = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                             '<![LOG[[Win32App] CDN mode, download completes.]')
            if locate_result_3 < 0 or locate_result_4 < 0:
                log_output = log_output + line_time[0] + " " + line_time[
                    1] + " CDN mode failed."
                log_output += '\n'
                log_output = log_output + line_time[0] + " " + line_time[1] + " Error downloading app."
                log_output += '\n'
                log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
                log_output += '\n'
                return log_output

            line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result_3])
            log_output = log_output + line_time[0] + " " + line_time[1] + " Start CDN mode download."
            log_output += '\n'
            line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result_4])
            log_output = log_output + line_time[0] + " " + line_time[1] + " CDN mode download completes."
            log_output += '\n'
            current_index += locate_result_4
        else:
            locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                         '<![LOG[Completing job ')
            if locate_result < 0:  # error downloading
                log_output = log_output + line_time[0] + " " + line_time[1] + " Error downloading app."
                log_output += '\n'
                log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
                log_output += '\n'
                return log_output

            line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result])
            log_output = log_output + line_time[0] + " " + line_time[1] + " Download completed."
            log_output += '\n'
            current_index += locate_result

        locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] file hash validation')
        if locate_result < 0:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Error hash validating app."
            log_output += '\n'
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
            log_output += '\n'
            return log_output

        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result])
        if win32_app_log[current_index + locate_result].startswith(
                '<![LOG[[Win32App] file hash validation pass, starts decrypting]'):
            log_output = log_output + line_time[0] + " " + line_time[1] + " Hash validation pass."
            log_output += '\n'
        else:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Hash validation failed."
            log_output += '\n'

        current_index += locate_result
        locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] Decryption')
        if locate_result < 0:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Error Decrypting app."
            log_output += '\n'
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
            log_output += '\n'
            return log_output

        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result])
        if win32_app_log[current_index + locate_result].startswith(
                '<![LOG[[Win32App] Decryption is done successfully.'):
            log_output = log_output + line_time[0] + " " + line_time[1] + " Decryption is done successfully."
            log_output += '\n'
        else:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Decryption failed."
            log_output += '\n'

        current_index += locate_result

        locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] Start unzipping.')
        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result])

        if locate_result < 0:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Error Unzipping app."
            log_output += '\n'
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
            log_output += '\n'
            return log_output

        log_output = log_output + line_time[0] + " " + line_time[1] + " Start unzipping."
        log_output += '\n'

    elif locate_result_2 >= 0:
        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result_2])
        log_output = log_output + line_time[0] + " " + line_time[1] + " Start downloading app."
        log_output += '\n'

        current_index += locate_result_2
        locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                         '<![LOG[[ExternalCDN] ExternalCDN App Content downloaded and verified')

        if locate_result < 0:  # error downloading
            log_output = log_output + line_time[0] + " " + line_time[1] + " Error downloading app."
            log_output += '\n'
            log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
            log_output += '\n'
            return log_output

        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result])
        log_output = log_output + line_time[0] + " " + line_time[1] + " Download completed."
        log_output += '\n'

        log_output = log_output + line_time[0] + " " + line_time[
            1] + " ExternalCDN App Content downloaded and verified, skip unzipping."
        log_output += '\n'

        current_index += locate_result

    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== ExecuteWithRetry]LOG]')
    if locate_result < 0:
        return ""  # abort this app log
    current_index += locate_result

    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] SetCurrentDirectory:')
    if locate_result < 0:
        return ""  # abort this app log
    current_index += locate_result

    app_context_index = current_index + 1
    install_command_index = current_index - 1
    line_time = get_timestamp_by_line(win32_app_log[app_context_index])

    if win32_app_log[app_context_index].startswith('<![LOG[[Win32App] Launch Win32AppInstaller in machine session'):
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Install Context is SYSTEM"
    elif win32_app_log[app_context_index].startswith('<![LOG[[Win32App] Trying to get elevated token for user.]'):
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Install Context is USER"
    else:
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Install Context is UNKNOWN"
    log_output += '\n'

    end_place = win32_app_log[install_command_index].find("]LOG]!")
    if intent == "UNINSTALL":
        log_output = log_output + line_time[0] + " " + line_time[1] + " UNINSTALL command: " \
                     + win32_app_log[install_command_index][7:end_place]
    else:
        log_output = log_output + line_time[0] + " " + line_time[1] + " Install command: " \
                     + win32_app_log[install_command_index][7:end_place]
    log_output += '\n'


    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Create installer process successfully.')
    if locate_result < 0:
        log_output = log_output + line_time[0] + " " + line_time[1] + " Error creating installer process."
        log_output += '\n'
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
        log_output += '\n'
        return log_output
    current_index += locate_result

    line_time = get_timestamp_by_line(win32_app_log[current_index])
    log_output = log_output + line_time[0] + " " + line_time[1] + " Installer process created successfully."
    log_output += '\n'

    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Installation is done, collecting result]')
    if locate_result < 0:
        log_output = log_output + line_time[0] + " " + line_time[1] + " Error Installing app."
        log_output += '\n'
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
        log_output += '\n'
        return log_output
    current_index += locate_result

    line_time = get_timestamp_by_line(win32_app_log[current_index])
    log_output = log_output + line_time[0] + " " + line_time[1] + " Installation is done."
    log_output += '\n'

    locate_result_1 = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] lpExitCode is defined as')
    locate_result_2 = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Admin did NOT set any return codes for app')

    if locate_result_1 < 0 and locate_result_2 < 0:
        pass
    elif locate_result_1 >= 0:
        line_time = get_timestamp_by_line(win32_app_log[current_index + locate_result_1])
        end_place = win32_app_log[current_index + locate_result_1].find("]LOG]!")
        if intent == "UNINSTALL":
            log_output = log_output + line_time[0] + " " + line_time[1] + " Un-installation Result is " + \
                         win32_app_log[current_index + locate_result_1][43:end_place]
        else:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Installation result is " + \
                         win32_app_log[current_index + locate_result_1][43:end_place]
        log_output += '\n'
        current_index += locate_result_1

    elif locate_result_2 >= 0:
        result_index = locate_result_2 + current_index + 1
        line_time = get_timestamp_by_line(win32_app_log[result_index])
        end_place = win32_app_log[result_index].find("]LOG]!")
        if intent == "UNINSTALL":
            log_output = log_output + line_time[0] + " " + line_time[1] + " Un-installation Result is " + \
                         win32_app_log[result_index][47:end_place]
        else:
            log_output = log_output + line_time[0] + " " + line_time[1] + " Installation result is " + \
                         win32_app_log[result_index][47:end_place]
        log_output += '\n'
        current_index += locate_result_2

    # log post detection - mandatory
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Detection rules after Execution')
    if locate_result < 0:
        log_output = log_output + line_time[0] + " " + line_time[1] + " Error detecting after execution."
        log_output += '\n'
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
        log_output += '\n'
        return log_output

    current_index += locate_result
    locate_result = locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Completed detectionManager')
    if locate_result < 0:  # exception and stop
        log_output = log_output + line_time[0] + " " + line_time[1] + " Error detecting after execution."
        log_output += '\n'
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL"
        log_output += '\n'
        return log_output
    current_index += locate_result
    line_time = get_timestamp_by_line(win32_app_log[current_index])
    start_place = win32_app_log[current_index].find("applicationDetectedByCurrentRule") + 34
    end_place = win32_app_log[current_index].find("]LOG]!")
    if win32_app_log[current_index][start_place:end_place] == "True":
        app_found = "App is installed"
        post_process_detect = True
    else:
        app_found = "App is NOT installed"
    log_output = log_output + line_time[0] + " " + line_time[1] + " Detect app after installation: " + app_found
    log_output += '\n'

    if (intent == "REQUIRED INSTALL" or intent == "AVAILABLE INSTALL") and post_process_detect:
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: SUCCESS "
        log_output += '\n'
    elif intent == "UNINSTALL" and not post_process_detect:
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Un-installation Result: SUCCESS "
        log_output += '\n'
    elif intent == "UNINSTALL" and post_process_detect:
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Un-installation Result: FAIL "
        log_output += '\n'
    else:
        log_output = log_output + line_time[0] + " " + line_time[1] + " App Installation Result: FAIL "
        log_output += '\n'

    return log_output


def process_win32_poller(win32_poller_log):
    if not win32_poller_log[0].startswith('<![LOG[[Win32App] ----------------------------------------------------- application poller starts.'):
        return None
    log_output = ""
    app_processing_line_start = []
    app_processing_line_stop = []
    for i in range(len(win32_poller_log)):
        eachline = win32_poller_log[i]
        # if eachline.startswith('<![LOG[[Win32App] The EspPhase:'):  # get ESP phase
        #     endplace = eachline.find("]LOG]!")
        #     log_output += eachline[:endplace]
        #     log_output += "\n"
        # elif eachline.startswith('<![LOG[After impersonation:'):  # get current user session
        #     endplace = eachline.find("]LOG]!")
        #     log_output = log_output + "Current user is: " + eachline[29:endplace]
        #     log_output += "\n"
        if eachline.startswith('<![LOG[[Win32App] ExecManager: processing targeted app'):
            if len(app_processing_line_start) == len(app_processing_line_stop):  # start app processing
                app_processing_line_start.append(i)
            elif len(app_processing_line_start) == len(app_processing_line_stop) + 1:  # dump incomplete app log
                del app_processing_line_start[-1]
                app_processing_line_start.append(i)
            else:
                del app_processing_line_start[len(app_processing_line_stop):]
                app_processing_line_start.append(i)
        elif eachline.startswith('<![LOG[[Win32App] app result (id ='):
            app_processing_line_stop.append(i+1)
    for i in range(len(app_processing_line_start)):
        result = process_each_app_log(win32_poller_log[app_processing_line_start[i]:app_processing_line_stop[i]])
        if result:
            log_output += result
    return log_output

from tkinter import *
from tkinter import ttk
from tkinter import filedialog


class Root(Tk):
    def __init__(self):
        super(Root, self).__init__()
        self.title("IME log Interpreter  V1.0")
        self.minsize(640, 400)
        # self.wm_iconbitmap('icon.ico')

        self.labelFrame = ttk.LabelFrame(self, text="Open File")
        self.labelFrame.grid(column=0, row=1, padx=20, pady=20)
        self.label = ttk.Label(self.labelFrame, text="")
        self.label.grid(column=1, row=2)

        self.button()
        self.button_analyze()
        self.button_clear()
        self.text_output()

    def button(self):
        self.button = ttk.Button(self.labelFrame, text="Browse IME log File", command=self.fileDialog)
        self.button.grid(column=1, row=1)

    def button_analyze(self):
        self.button_analyze = ttk.Button(self.labelFrame, text="Start Analyzing", command=lambda: self.start_analyze(self.filename))
        self.button_analyze.grid(column=2, row=1)

    def button_clear(self):
        self.button_clear = ttk.Button(self.labelFrame, text="Clear Result", command=self.clear_result)
        self.button_clear.grid(column=2, row=2)

    def text_output(self):
        # Create text widget and specify size.
        self.text_output = Text(self.labelFrame, height=35, width=152, font=('Times New Roman',12))
        self.text_output.grid(column=1, row=3)

    def clear_result(self):
        self.text_output.delete("1.0","end")

    def fileDialog(self):
        self.filename = filedialog.askopenfilename(initialdir="/", title="Select A File",
                                                   filetype=(("IME log files", "*.log"), ("all files", "*.*")))
        self.label.configure(text="")
        self.label.configure(text=self.filename)

    def start_analyze(self, IME_log_path):
        output = start_process_by_log_path(IME_log_path)
        self.text_output.delete("1.0","end")
        self.text_output.insert(END, output)


def start_process_by_log_path(IME_log_path):
    # IME_log_path = "C:\\test\\IntuneManagementExtension.log"
    loadedLog = load_IME_log(IME_log_path)
    outputlog = ""
    win32_poller_lines = get_Win32_poller_lines(loadedLog)
    powershell_poller_lines = get_powershell_poller_lines(loadedLog)
    for i in range(len(win32_poller_lines[0])):
        result = process_win32_poller(loadedLog[win32_poller_lines[0][i]:win32_poller_lines[1][i]])
        if result:
            thisdate, thistime = get_timestamp_by_line(loadedLog[win32_poller_lines[0][i]])
            outputlog = outputlog + "Application Poller " + thisdate + " " + thistime + " Starts" + "\n\n"
            outputlog += result
            outputlog = outputlog + "\n"
            thisdate, thistime = get_timestamp_by_line(loadedLog[win32_poller_lines[1][i] - 1])
            outputlog = outputlog + "Application Poller " + thisdate + " " + thistime + " Ends"
            outputlog = outputlog + "\n\n\n"
    if outputlog == "":
        outputlog = "No App Processing Log found."
    # print(outputlog)
    # print()
    return outputlog


if __name__ == "__main__":
    root = Root()
    root.mainloop()
    #start_process_by_log_path("")

