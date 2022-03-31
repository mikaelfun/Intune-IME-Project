import Preprocessing as pp

log_output = ""


def add_line(new_line):
    global log_output
    log_output = log_output + "\n"
    log_output = log_output + new_line


def process_standalone_app(win32_app_log, intent):
    current_index = 0
    pre_process_detect = False
    post_process_detect = False

    # log skip due to WPJ and user context payload
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:], "<![LOG[[Win32App] Device is WPJ, and payload context is user, report not applicable]")
    if locate_result >= 0:  # exception and stop
        time_now = pp.get_timestamp_by_line(win32_app_log[locate_result])
        add_line(time_now + " Device is WPJ, and payload context is user, report not applicable!")
        add_line(time_now + " App Installation Result: NOT APPLICABLE")
        return log_output

    # log pre detection - mandatory
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Detection rules]')
    if locate_result < 0:  # exception and stop
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error locating pre-install detection line!")
    else:
        current_index += locate_result

        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] Completed detectionManager')
        if locate_result < 0:  # exception and stop
            time_now = pp.get_timestamp_by_line(win32_app_log[-1])
            add_line(time_now + " Error locating pre-install detection result!")
        else:
            current_index += locate_result
            time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
            start_place = win32_app_log[current_index].find("applicationDetectedByCurrentRule") + 34
            end_place = win32_app_log[current_index].find("]LOG]!")
            if win32_app_log[current_index][start_place:end_place] == "True":
                app_found = "App is installed"
                pre_process_detect = True
            else:
                app_found = "App is NOT installed"
            add_line(time_now + " Detect app before processing: " + app_found)

        if intent == "UNINSTALL":
            if not pre_process_detect:
                add_line(time_now + " Intent is UNINSTALL and app is not detected.")
                add_line(time_now + " App Un-installation Result: SUCCESS ")
                return log_output
        elif intent == "REQUIRED INSTALL" or intent == "AVAILABLE INSTALL":
            if pre_process_detect:
                add_line(time_now + " App Installation Result: SUCCESS ")
                return log_output
        else:
            pass

    # log applicability check - mandatory
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Check applicability')
    if locate_result < 0:  # exception and stop
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error locating Applicability check!")
    else:
        current_index += locate_result
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
        if "intent is to un-install, skip applicability check" in win32_app_log[current_index + 1]:
            add_line(
                time_now + " Intent is UNINSTALL and app is NOT detected.")

            add_line(time_now + " App Un-installation Result: SUCCESS ")
            return log_output
        elif "intent is to install, skip applicability check" in win32_app_log[current_index + 1]:
            add_line(time_now + " Intent is INSTALL and app is detected.")
            add_line(time_now + " App Installation Result: SUCCESS ")
            return log_output

    # log extended applicability check - optional
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Check Extended requirement rules')
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error locating Extended requirement check!")
    else:
        basic_applicability = True
        basic_applicability_reason = ""
        extended_applicability = False
        extended_applicability_reason = ""

        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])

        for applicability_index in range(current_index + 1, current_index + locate_result):
            if win32_app_log[applicability_index].startswith("<![LOG[[Win32App]") and "skip check." not in win32_app_log[applicability_index] and \
                    "applicability: Applicable" not in win32_app_log[applicability_index]:
                basic_applicability = False
                end_place = win32_app_log[applicability_index].find("applicability:")
                basic_applicability_reason = win32_app_log[applicability_index][49:end_place - 2]

        if not basic_applicability:
            add_line(time_now + " Basic Applicability Check: Not Applicable, reason is: " + basic_applicability_reason)
            if intent == "UNINSTALL":
                add_line(time_now + " App Un-installation Result: NOT APPLICABLE")
            else:
                add_line(
                    time_now + " App Installation Result: NOT APPLICABLE")
            return log_output
        else:
            add_line(time_now + " Basic Applicability Check: Applicable")
        current_index = current_index + locate_result + 1
        if win32_app_log[current_index].startswith(
                '<![LOG[[Win32App] No ExtendedRequirementRules for this App. Skipping Check Extended requirement rule'):
            extended_applicability = True
        else:
            locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                           '<![LOG[[Win32App] Extended requirement rules processing complete. isApplicationApplicable: ')
            if locate_result < 0:
                time_now = pp.get_timestamp_by_line(win32_app_log[-1])
                add_line(time_now + " Error locating Extended requirement result!")
            else:
                current_index += locate_result
                if win32_app_log[current_index].startswith('<![LOG[[Win32App] Extended requirement rules processing complete. isApplicationApplicable: Applicable'):
                    extended_applicability = True
                else:
                    end_place = win32_app_log[current_index].find("]LOG]!")
                    extended_applicability_reason = win32_app_log[current_index][91:end_place]

        time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
        if not extended_applicability:
            add_line(time_now + " Extended Applicability Check: Not Applicable, reason is: " + extended_applicability_reason)
            if intent == "UNINSTALL":
                add_line(time_now + " App Un-installation Result: NOT APPLICABLE")
            else:
                add_line(time_now + " App Installation Result: NOT APPLICABLE")
            return log_output
        else:
            add_line(time_now + " Extended Applicability Check: Applicable")

    # log detection without existing AppResult (GRS) - optional
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Check detection without existing AppResult')
    current_index += locate_result

    time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " ===Step=== Check detection without existing AppResult MISSING!")


    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index+1:],
                                                   '<![LOG[[Win32App] ===Step===')
    if locate_result <= 0: # check if GRS situation
        for grs_index in range(current_index, len(win32_app_log)):
            time_now = pp.get_timestamp_by_line(win32_app_log[grs_index])
            if win32_app_log[grs_index].startswith(
                    '<![LOG[[Win32App] Tried in last 24 hours, No need to exec. skip execution'):
                add_line(time_now + " Still in GRS, tried in last 24 hours, skip execution.")
                add_line(time_now + " App Installation Result: SKIP due to GRS")
                return log_output
            elif win32_app_log[grs_index].startswith('<![LOG[[Win32App] GRS is expired. kick off download & install'):
                add_line(time_now + " GRS is expired. kick off download & install.")
                break
            else:
                pass

    for grs_index in range(current_index, current_index + locate_result):
        time_now = pp.get_timestamp_by_line(win32_app_log[grs_index])
        if win32_app_log[grs_index].startswith('<![LOG[[Win32App] Tried in last 24 hours, No need to exec. skip execution'):
            add_line(time_now + " Still in GRS, tried in last 24 hours, skip execution.")
            add_line(time_now + " App Installation Result: SKIP due to GRS")
            return log_output
        elif win32_app_log[grs_index].startswith('<![LOG[[Win32App] GRS is expired. kick off download & install'):
            add_line(time_now + " GRS is expired. kick off download & install.")
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
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Download]LOG]!')
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error locating Download step!")

    current_index += locate_result
    locate_result_1 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[Starting job ') # sign of DO download
    locate_result_2 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                    '<![LOG[[Win32App] ExternalCDN mode, content raw URL is') # sign of CDN mode
    locate_result_3 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                        '<![LOG[[Win32App] Content cache found for app')

    locate_result_4 = pp.locate_line_startswith_keyword(win32_app_log[current_index:], '<![LOG[[Win32App DO] DO Job set priority is ')

    if locate_result_1 < 0 and locate_result_2 < 0 and locate_result_3 < 0:
        add_line(time_now + " Error locating Downloading status!")
    elif locate_result_1 >= 0: #DO mode
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_1])
        if locate_result_4 >= 0:
            end_place = win32_app_log[current_index+locate_result_4].find(']LOG]!')
            DO_priority = win32_app_log[current_index+locate_result_4][44:end_place]
            if DO_priority == "BG_JOB_PRIORITY_NORMAL":
                DO_time_out = "10 minutes"
                DO_priority_converted = "Content Download in Background"
            elif DO_priority == "BG_JOB_PRIORITY_FOREGROUND":
                DO_time_out = "12 hours"
                DO_priority_converted = "Content Download in Foreground"

            add_line(time_now + " Start downloading app using DO.")
            add_line(time_now + " DO Download priority is: " + DO_priority_converted + ", Time out is: "+DO_time_out)
            '''
            <![LOG[[Win32App DO] DO Job set priority is BG_JOB_PRIORITY_NORMAL == time out is 600000 ms
            <![LOG[[Win32App DO] DO Job set priority is BG_JOB_PRIORITY_FOREGROUND == time out is 43200000 ms
            '''
        else:
            add_line(time_now + " Error locating DO priority!")
            add_line(time_now + " Start downloading app using DO.")

        current_index += locate_result_1
        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:], '<![LOG[Job has failed.')
        if locate_result >= 0: # DO fail
            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])
            add_line(time_now + " DO Download Job failed. Trying CDN mode.")

            locate_result_3 = pp.locate_line_startswith_keyword(win32_app_log[current_index:], '<![LOG[[Win32App] ExternalCDN mode, content raw URL is')
            locate_result_4 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                             '<![LOG[[Win32App] CDN mode, download completes.')
            if locate_result_3 < 0 or locate_result_4 < 0:
                add_line(time_now + " CDN mode failed.")

                add_line(time_now + " Error downloading app.")
                bytes_downloaded_line_index = pp.locate_line_startswith_keyword_backward(win32_app_log[current_index:],
                                                                                         "<![LOG[[StatusService] Downloading app (id = ")
                if bytes_downloaded_line_index >= 0:
                    start_place = win32_app_log[current_index + bytes_downloaded_line_index].find("via CDN, ") + 9
                    end_place = win32_app_log[current_index + bytes_downloaded_line_index].find("]LOG]!>")
                    bytes_downloaded = win32_app_log[current_index + bytes_downloaded_line_index][start_place:end_place]
                    time_now = pp.get_timestamp_by_line(win32_app_log[current_index + bytes_downloaded_line_index])
                    add_line(time_now + " Downloaded size: " + bytes_downloaded)
                else:
                    add_line(time_now + " Error locating downloaded size!")

                add_line(time_now + " App Installation Result: FAIL")

                return log_output

            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_3])
            add_line(time_now + " Start CDN mode download.")

            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_4])
            add_line(time_now + " CDN mode download completes.")

            current_index += locate_result_4
        else: # DO success
            locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                         '<![LOG[Completing job ')
            if locate_result < 0:  # error downloading
                time_now = pp.get_timestamp_by_line(win32_app_log[-1])
                add_line(time_now + " Error downloading app via DO!")
                bytes_downloaded_line_index = pp.locate_line_startswith_keyword_backward(win32_app_log[current_index:], "<![LOG[[StatusService] Downloading app (id = ")
                if bytes_downloaded_line_index >= 0:
                    start_place = win32_app_log[current_index + bytes_downloaded_line_index].find("via DO, ") + 8
                    end_place = win32_app_log[current_index + bytes_downloaded_line_index].find("]LOG]!>")
                    bytes_downloaded = win32_app_log[current_index + bytes_downloaded_line_index][start_place:end_place]
                    time_now = pp.get_timestamp_by_line(win32_app_log[current_index + bytes_downloaded_line_index])
                    add_line(time_now + " Downloaded size: " + bytes_downloaded)
                else:
                    add_line(time_now + " Error locating downloaded size!")

                add_line(time_now + " App Installation Result: FAIL")
                return log_output

            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])
            add_line(time_now + " DO mode download completed.")

            current_index += locate_result

        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] file hash validation')
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])
        if locate_result < 0:
            time_now = pp.get_timestamp_by_line(win32_app_log[-1])
            add_line(time_now + " Error hash validating app!")

            add_line(time_now + " App Installation Result: FAIL")

            return log_output

        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])
        if win32_app_log[current_index + locate_result].startswith(
                '<![LOG[[Win32App] file hash validation pass, starts decrypting]'):
            add_line(time_now + " Hash validation pass.")

        else:
            add_line(time_now + " Hash validation failed.")


        current_index += locate_result
        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] Decryption')
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
        if locate_result < 0:
            time_now = pp.get_timestamp_by_line(win32_app_log[-1])
            add_line(time_now + " Error Decrypting app!")

            add_line(time_now + " App Installation Result: FAIL")

            return log_output

        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])
        if win32_app_log[current_index + locate_result].startswith(
                '<![LOG[[Win32App] Decryption is done successfully.'):
            add_line(time_now + " Decryption is done successfully.")

        else:
            add_line(time_now + " Decryption failed!")
            add_line(time_now + " App Installation Result: FAIL")

            return log_output

        current_index += locate_result

        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] Start unzipping.')
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])

        if locate_result < 0:
            time_now = pp.get_timestamp_by_line(win32_app_log[-1])
            add_line(time_now + " Error Unzipping app!")

            add_line(time_now + " App Installation Result: FAIL")

            return log_output

        add_line(time_now + " Start unzipping.")

    elif locate_result_2 >= 0: # CDN mode
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_2])
        add_line(time_now + " Start downloading app via CDN.")

        current_index += locate_result_2
        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                         '<![LOG[[ExternalCDN] ExternalCDN App Content downloaded and verified')
        locate_result_5 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],"<![LOG[[Win32App] CDN mode, download completes.")
        if locate_result < 0 and locate_result_5 < 0:  # error downloading
            time_now = pp.get_timestamp_by_line(win32_app_log[-1])
            add_line(time_now + " Error downloading app using CDN!")
            bytes_downloaded_line_index = pp.locate_line_startswith_keyword_backward(win32_app_log[current_index:],
                                                                                     "<![LOG[[StatusService] Downloading app (id = ")
            if bytes_downloaded_line_index >= 0:
                start_place = win32_app_log[current_index + bytes_downloaded_line_index].find("via CDN, ") + 9
                end_place = win32_app_log[current_index + bytes_downloaded_line_index].find("]LOG]!>")
                bytes_downloaded = win32_app_log[current_index + bytes_downloaded_line_index][start_place:end_place]
                time_now = pp.get_timestamp_by_line(win32_app_log[current_index + bytes_downloaded_line_index])
                add_line(time_now + " Downloaded size: " + bytes_downloaded)
            else:
                add_line(time_now + " Error locating downloaded size!")

            add_line(time_now + " App Installation Result: FAIL")

            return log_output
        elif locate_result_5 >= 0:  # normal CDN mode
            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_5])
            add_line(time_now + " Download completed using CDN.")

            current_index += locate_result_5
            locate_result_6 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                              '<![LOG[[Win32App] file hash validation')
            if locate_result_6 < 0:
                time_now = pp.get_timestamp_by_line(win32_app_log[-1])
                add_line(time_now + " Error hash validating app!")
                add_line(time_now + " App Installation Result: FAIL")
                return log_output

            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_6])
            if win32_app_log[current_index + locate_result_6].startswith(
                    '<![LOG[[Win32App] file hash validation pass, starts decrypting]'):
                add_line(time_now + " Hash validation pass.")

            else:
                add_line(time_now + " Hash validation failed.")

            current_index += locate_result_6
            locate_result_7 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                              '<![LOG[[Win32App] Decryption')
            time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
            if locate_result_7 < 0:
                time_now = pp.get_timestamp_by_line(win32_app_log[-1])
                add_line(time_now + " Error Decrypting app!")
                add_line(time_now + " App Installation Result: FAIL")
                return log_output

            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_7])
            if win32_app_log[current_index + locate_result_7].startswith(
                    '<![LOG[[Win32App] Decryption is done successfully.'):
                add_line(time_now + " Decryption is done successfully.")

            else:
                add_line(time_now + " Decryption failed!")
                add_line(time_now + " App Installation Result: FAIL")

                return log_output

            current_index += locate_result_7

            locate_result_8 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                              '<![LOG[[Win32App] Start unzipping.')
            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_8])

            if locate_result_8 < 0:
                time_now = pp.get_timestamp_by_line(win32_app_log[-1])
                add_line(time_now + " Error Unzipping app!")
                add_line(time_now + " App Installation Result: FAIL")
                return log_output

            add_line(time_now + " Start unzipping.")
            current_index += locate_result_8

        elif locate_result >= 0:  # Edge CDN mode

            time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_2])
            add_line(time_now + " Download completed using CDN.")

            add_line(time_now + " ExternalCDN App Content downloaded and verified, skip unzipping.")

            current_index += locate_result

    elif locate_result_3 >= 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_3])
        add_line(time_now + " Content cache found, skip Downloading.")

        current_index += locate_result_3

    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== ExecuteWithRetry]LOG]')
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error locating Install log!")
        return log_output
    else:
        current_index += locate_result

        locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                       '<![LOG[[Win32App] SetCurrentDirectory:')
        if locate_result < 0:
            time_now = pp.get_timestamp_by_line(win32_app_log[-1])
            add_line(time_now + " Error locating install directory!")
        else:
            current_index += locate_result

            app_context_index = current_index + 1
            install_command_index = current_index - 1
            time_now = pp.get_timestamp_by_line(win32_app_log[app_context_index])

            if win32_app_log[app_context_index].startswith('<![LOG[[Win32App] Launch Win32AppInstaller in machine session'):
                add_line(time_now + " App Install Context is SYSTEM")
            elif win32_app_log[app_context_index].startswith('<![LOG[[Win32App] Trying to get elevated token for user.]'):
                add_line(time_now + " App Install Context is USER")
            else:
                add_line(time_now + " App Install Context is UNKNOWN")

            end_place = win32_app_log[install_command_index].find("]LOG]!")
            if intent == "UNINSTALL":
                add_line(time_now + " UNINSTALL command: " \
                             + win32_app_log[install_command_index][7:end_place])
            else:
                add_line(time_now + " Install command: " \
                             + win32_app_log[install_command_index][7:end_place])

    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Create installer process successfully.')
    time_now = pp.get_timestamp_by_line(win32_app_log[current_index])

    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error creating installer process.")

        add_line(time_now + " App Installation Result: FAIL")

        return log_output

    current_index += locate_result

    time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
    add_line(time_now + " Installer process created successfully. Installer time out is 60 minutes.")

    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Installation is done, collecting result]')
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error Installing app.")

        add_line(time_now + " App Installation Result: FAIL")

        return log_output
    current_index += locate_result

    time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
    add_line(time_now + " Installation is done.")

    locate_result_1 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] lpExitCode is defined as')
    locate_result_2 = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Admin did NOT set mapping for lpExitCode: ')

    if locate_result_1 < 0 and locate_result_2 < 0:
        add_line(time_now + " Error locating install exit code!")
    elif locate_result_1 >= 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result_1])
        end_place = win32_app_log[current_index + locate_result_1].find("]LOG]!")
        if intent == "UNINSTALL":
            add_line(time_now + " Un-installation Result is " + \
                         win32_app_log[current_index + locate_result_1][43:end_place])
        else:
            add_line(time_now + " Installation result is " + \
                         win32_app_log[current_index + locate_result_1][43:end_place])

        current_index += locate_result_1

    elif locate_result_2 >= 0:
        result_index = locate_result_2 + current_index + 1
        time_now = pp.get_timestamp_by_line(win32_app_log[result_index])
        end_place = win32_app_log[result_index].find("]LOG]!")
        if intent == "UNINSTALL":
            add_line(time_now + " Result is " + \
                         win32_app_log[result_index][47:end_place])
        else:
            add_line(time_now + " Installation result is " + \
                         win32_app_log[result_index][47:end_place])

        current_index += locate_result_2

    # log restart behavior
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] DeviceRestartBehavior: ')
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error detecting restart behavior.")
    else:
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index + locate_result])
        restart_behavior_index = win32_app_log[current_index + locate_result][41:42]
        if restart_behavior_index == "0":
            add_line(time_now + " Restart behavior: [Restart determined by return codes]")
        elif restart_behavior_index == "1":
            add_line(time_now + " Restart behavior: [App may force a device restart]")
        elif restart_behavior_index == "2":
            add_line(time_now + " Restart behavior: [No specific action]")
        elif restart_behavior_index == "3":
            add_line(time_now + " Restart behavior: [Intune will force restart]")
        else:
            add_line(time_now + " Restart behavior: Unknown code: " + restart_behavior_index)


    # log post detection - mandatory
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] ===Step=== Detection rules after Execution')
    if locate_result < 0:
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Error detecting after execution.")

        add_line(time_now + " App Installation Result: FAIL")

        return log_output

    current_index += locate_result
    locate_result = pp.locate_line_startswith_keyword(win32_app_log[current_index:],
                                                   '<![LOG[[Win32App] Completed detectionManager')

    if locate_result < 0:  # exception and stop
        time_now = pp.get_timestamp_by_line(win32_app_log[-1])
        add_line(time_now + " Failed to locate detection result after execution!")

        add_line(time_now + " App Installation Result: FAIL")

        return log_output
    else:
        current_index += locate_result
        time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
        start_place = win32_app_log[current_index].find("applicationDetectedByCurrentRule") + 34
        end_place = win32_app_log[current_index].find("]LOG]!")
        if win32_app_log[current_index][start_place:end_place] == "True":
            app_found = "App is installed"
            post_process_detect = True
        else:
            app_found = "App is NOT installed"
        add_line(time_now + " Detect app after installation: " + app_found)

        if (intent == "REQUIRED INSTALL" or intent == "AVAILABLE INSTALL") and post_process_detect:
            add_line(time_now + " App Installation Result: SUCCESS ")

        elif intent == "UNINSTALL" and not post_process_detect:
            add_line(time_now + " App Un-installation Result: SUCCESS ")

        elif intent == "UNINSTALL" and post_process_detect:
            add_line(time_now + " App Un-installation Result: FAIL ")

        else:
            add_line(time_now + " App Installation Result: FAIL ")

    return log_output


def get_dependent_apps_start_stop_lines(win32_app_log):
    dependent_apps_start_lines = []
    dependent_apps_stop_lines = []
    for line_index in range(len(win32_app_log)):
        if win32_app_log[line_index].startswith("<![LOG[[Win32App] Aggregated result for ("):
            start_place = 41
            end_place = 77
            app_id = win32_app_log[line_index][start_place: end_place]
            search_string = "<![LOG[[Win32App] added new report for " + app_id
            app_result_line = pp.locate_line_startswith_keyword(win32_app_log[line_index:], search_string)

            if app_result_line > 0:
                dependent_apps_start_lines.append(line_index+1)
                dependent_apps_stop_lines.append(app_result_line + line_index)
            else:
                pass  # dump invalid app log

    return dependent_apps_start_lines, dependent_apps_stop_lines


def process_dependency_apps(win32_app_log, dependent_apps_start_lines, dependent_apps_stop_lines):
    for each_dependent_app_index in range(len(dependent_apps_start_lines)):
        name_start_index = win32_app_log[dependent_apps_start_lines[each_dependent_app_index]].find("name = ") + 7
        name_end_index = win32_app_log[dependent_apps_start_lines[each_dependent_app_index]].find(") with mode =")
        id_start_index = win32_app_log[dependent_apps_start_lines[each_dependent_app_index]].find("Processing app (id=") + 19
        id_stop_index = win32_app_log[dependent_apps_start_lines[each_dependent_app_index]].find(", name =")
        current_dependent_app_name = win32_app_log[dependent_apps_start_lines[each_dependent_app_index]][name_start_index:name_end_index]
        current_dependent_app_id = win32_app_log[dependent_apps_start_lines[each_dependent_app_index]][id_start_index: id_stop_index]
        time_now = pp.get_timestamp_by_line(win32_app_log[dependent_apps_start_lines[each_dependent_app_index]])
        add_line("")
        add_line(time_now + " Processing Dependent app [" + current_dependent_app_name + "]")
        process_standalone_app(win32_app_log[dependent_apps_start_lines[each_dependent_app_index]: dependent_apps_stop_lines[each_dependent_app_index]], "REQUIRED INSTALL")
        add_line("")


def process_each_app_log(win32_app_log):
    add_line("\n")
    global log_output
    log_output = ""
    if not win32_app_log:
        return log_output
    # i = 0
    intent = "UNKNOWN"
    current_index = 0
    pre_process_detect = False
    post_process_detect = False


    time_now = pp.get_timestamp_by_line(win32_app_log[0])
    if not win32_app_log[0].startswith('<![LOG[[Win32App] ExecManager: processing targeted app'):  # exception and stop
        add_line(time_now + " Error locating App intent info!")
    else:
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
        name_index = win32_app_log[0].find("name='")
        name_index_stop = win32_app_log[0].find("', id='")
        app_name = win32_app_log[0][name_index+6:name_index_stop]

        locate_result1 = pp.locate_line_startswith_keyword(win32_app_log,
                                                          '<![LOG[[Win32App] This is a standalone app,')
        locate_result2 = pp.locate_line_startswith_keyword(win32_app_log,
                                                          '<![LOG[[Win32App] ProcessDetectionRules starts]LOG]')
        if locate_result1 > 0:
            add_line(time_now + " Processing Standalone app: [" + \
                     app_name + "] with intent " + intent)
            process_standalone_app(win32_app_log[locate_result1:], intent)
        # Dependency flow
        elif locate_result2 > 0:
            # dependency flow, first check target app detection
            add_line(time_now + " Processing app with dependency: [" + \
                     app_name + "] with intent " + intent)
            locate_result = pp.locate_line_startswith_keyword(win32_app_log,
                                                              '<![LOG[[Win32App] Completed detectionManager')
            if locate_result < 0:  # exception and stop
                time_now = pp.get_timestamp_by_line(win32_app_log[-1])
                add_line(time_now + " Failed to locate pre-dependency app detection result!")
                add_line(time_now + " App Installation Result: FAIL")

                return log_output
            else:
                current_index += locate_result
                time_now = pp.get_timestamp_by_line(win32_app_log[current_index])
                start_place = win32_app_log[current_index].find("applicationDetectedByCurrentRule: ") + 34
                end_place = win32_app_log[current_index].find("]LOG]!")
                if win32_app_log[current_index][start_place:end_place] == "True":
                    app_found = "App is installed"
                    pre_process_detect = True
                else:
                    app_found = "App is NOT installed"
                add_line(time_now + " Detect app before installation: " + app_found)

                if intent == "UNINSTALL":
                    if not pre_process_detect:
                        add_line(time_now + " Intent is UNINSTALL and app is not detected.")
                        add_line(time_now + " App Un-installation Result: SUCCESS ")
                        return log_output
                elif intent == "REQUIRED INSTALL" or intent == "AVAILABLE INSTALL":
                    if pre_process_detect:
                        add_line(time_now + " App Installation Result: SUCCESS ")
                        return log_output
            if win32_app_log[current_index+1].startswith("<![LOG[[Win32App] starts processing the app chain for app"):
                add_line(time_now + " Processing Dependent app chain.")
                add_line("")
                dependent_app_lines_start, dependent_app_lines_stop = get_dependent_apps_start_stop_lines(win32_app_log[current_index+1:])

                process_dependency_apps(win32_app_log[current_index+1:], dependent_app_lines_start, dependent_app_lines_stop)

                add_line("")
                add_line(time_now + " All dependent apps processed, processing target app [" + app_name + "] now.")
                add_line("")

                process_standalone_app(win32_app_log[dependent_app_lines_stop[-1]:], intent)

    return log_output
