"""
This is Class def for SubGraph.
Each Application Poller session may contain multiple SubGraphs to process
A SubGraph is a set of applications with all dependency/supercedence
A SubGraph can contain 1 single app without any dependency/supercedence
Create this class object for each SubGraph.

Error Code range: 4000 - 4999

Class hierarchy:
- ImeInterpreter
    - EMSLifeCycle
        - ApplicationPoller
            - SubGraph
                - Win32App

"""
from logprocessinglibrary import *
import json
from win32app import *
from win32app import Win32App


class SubGraph:
    def __init__(self, subgraph_processing_log, policy_json, last_enforcement_json_dict, reevaluation_time="Subgraph Not Evaluated before"):
        self.reevaluation_time = reevaluation_time
        self.reevaluation_expired = True
        self.hash_key = ""
        self.grs_time_list = dict()  # key: app id string, value: grs time string
        self.grs_expiry = dict()  # key: app id string, value: true(expired), false(not expired)
        self.app_num = 0
        self.log_content = subgraph_processing_log
        self.log_len = len(self.log_content)
        self.app_id_list = []
        self.app_names = dict()  # key: app id string, value: app name string
        self.policy_json = policy_json
        self.win32app_object_list = []
        self.is_stand_alone_subgraph = True
        self.last_enforcement_json_dict = last_enforcement_json_dict  # key: app id string, value: last_enforcement_json
        self.actual_app_id_to_install_list = []
        """ 
        <![LOG[[Win32App][ActionProcessor] Found: 1 apps with intent to install: [1f4b773e-53ed-4cd8-b12b-16c336bba549].]LOG]
        After dependency apps targeting evaluation, it will be reflected in this line to check whether each app should be processed.
        If not processed, it means some dependent app is not targeted or dependent app itself is not targeted
        """
        if self.log_len < 3:
            print("Error creating SubGraph Object!")
            print(subgraph_processing_log)
            return None
        self.process_subgraph_meta()
        self.get_app_name_from_json_by_app_id()
        self.initialize_win32_apps_list()

    def get_app_name_from_json_by_app_id(self):
        for cur_app_index in range(self.app_num):
            cur_app_name = [match['Name'] for match in self.policy_json if match['Id'] == self.app_id_list[cur_app_index]].pop()
            self.app_names[self.app_id_list[cur_app_index]] = cur_app_name
            # print(cur_app_name)

    def process_subgraph_meta(self):
        id_start_index = 65
        id_stop_index = self.log_content[0].find(']LOG]!')
        """
        Need to put the root app of dependency chain in first one.
        """
        self.app_id_list = list(
            (self.log_content[0][id_start_index:id_stop_index]).split(', '))
        # print(cur_subgraph.app_id_list)
        self.app_num = len(self.app_id_list)
        if self.app_num > 1:
            self.is_stand_alone_subgraph = False
            # print(self.log_content)
        for each_line_index in range(1, self.log_len):
            cur_line = self.log_content[each_line_index]
            if cur_line.startswith('<![LOG[[Win32App][GRSManager] Found GRS value:'):
                # app was processed before, saving hash key, grs time,
                grs_value_hash_index_start = 115
                grs_value_hash_index_end = grs_value_hash_index_start + CONST_GRS_HASH_KEY_LEN
                if self.hash_key == "":
                    self.hash_key = cur_line[grs_value_hash_index_start:grs_value_hash_index_end]
                app_id_index_end = cur_line.find('.]LOG]!')
                app_id_index_start = app_id_index_end - CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                grs_time_index_start = 47
                grs_time_index_end = 66
                cur_app_grs_time = cur_line[grs_time_index_start:grs_time_index_end]
                self.grs_time_list[cur_app_id] = cur_app_grs_time
                # print(self.hash_key)
            elif cur_line.startswith('<![LOG[[Win32App][GRSManager] App with id: '):
                app_id_index_start = cur_line.find('App with id: ') + 13
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                # print(cur_line[79:83])
                if "has no recorded GRS value" in cur_line:
                    # app has no grs found.
                    # <![LOG[[Win32App][GRSManager] App with id: 0557caed-3f50-499f-a39d-5b1179f78922 has no recorded GRS value which will be treated as expired.
                    grs_value_hash_index_start = 149
                    grs_value_hash_index_end = grs_value_hash_index_start + CONST_GRS_HASH_KEY_LEN
                    if self.hash_key == "":
                        self.hash_key = cur_line[grs_value_hash_index_start:grs_value_hash_index_end]
                    self.grs_expiry[cur_app_id] = True
                elif cur_line[79:83] == ' is ':
                    expiry_start_index = 83
                    expiry_end_index = cur_line.find('. | Hash =')
                    cur_app_expiry_string = cur_line[expiry_start_index:expiry_end_index]
                    if cur_app_expiry_string == 'not expired':
                        self.grs_expiry[cur_app_id] = False
                    elif cur_app_expiry_string == 'expired':
                        self.grs_expiry[cur_app_id] = True
            elif cur_line.startswith(
                    '<![LOG[[Win32App][ReevaluationScheduleManager] Subgraph reevaluation interval is not expired'):
                # meaning the current subgraph will not be processed
                self.reevaluation_expired = False
            # elif cur_line.startswith(
            #         '<![LOG[[Win32App][ReevaluationScheduleManager] Setting subgraph reevaluation time with value:'):
            #     index_subgraph_reevaluation_time_start = cur_line.find('time with value: ') + 17
            #     index_subgraph_reevaluation_time_end = cur_line.find(' for subgraph with hash')
            #     if self.reevaluation_time == "":
            #         self.reevaluation_time = cur_line[
            #                              index_subgraph_reevaluation_time_start:index_subgraph_reevaluation_time_end]
                # print(self.reevaluation_time)
            elif cur_line.startswith('<![LOG[[Win32App][ActionProcessor] Found: 1 apps with intent to install: '):
                app_id_index_start = cur_line.find('install: [') + 10
                app_id_index_end = app_id_index_start + CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                self.actual_app_id_to_install_list.append(cur_app_id)

    def initialize_win32_apps_list(self):
        for cur_app_index in range(self.app_num):
            cur_app_id = self.app_id_list[cur_app_index]
            cur_app_name = self.app_names[cur_app_id] if cur_app_id in self.app_names.keys() else ''
            cur_app_grs_time = self.grs_time_list[cur_app_id] if cur_app_id in self.grs_time_list.keys() else ''
            cur_app_grs_expiry = self.grs_expiry[cur_app_id] if cur_app_id in self.grs_expiry.keys() else False
            cur_app_last_enforcement_json = self.last_enforcement_json_dict[cur_app_id] \
                if cur_app_id in self.last_enforcement_json_dict.keys() else None
            self.win32app_object_list.append(Win32App(self.log_content, cur_app_id, cur_app_name, self.policy_json,
                                                      cur_app_grs_time, self.hash_key, cur_app_grs_expiry,
                                                      self.is_stand_alone_subgraph, cur_app_last_enforcement_json))

    def generate_subgraph_standalone_app_processing_log_output(self, app_object):
        interpreted_log_output = ""
        if not self.is_stand_alone_subgraph:
            print("Error in code! Standalone subgraph flow with dependency chain")
            return interpreted_log_output
        """
        For standalone app, there is just 1 app in the subgraph.
        Output app meta and app processing if any.
        """
        interpreted_log_output += app_object.generate_standalone_win32_app_meta_log_output()
        interpreted_log_output += '\n'

        interpreted_log_output += app_object.generate_win32app_log_output()
        interpreted_log_output += '\n'

    # Recursive function to handle dependency chain
    def generate_subgraph_dependent_app_processing_log_output(self, app_object, app_index):
        interpreted_log_output = ""
        interpreted_log_output += str(app_index) + '.\n'
        has_dependent_apps = True if app_object.dependent_apps_list is not None else False
        if not has_dependent_apps:
            interpreted_log_output += app_object.generate_standalone_win32_app_meta_log_output()
            interpreted_log_output += '\n'
            if self.reevaluation_expired:
                interpreted_log_output += app_object.generate_standalone_win32app_log_output()
                interpreted_log_output += '\n'
        else:
            interpreted_log_output += app_object.generate_dependency_win32_app_meta_log_output()
            interpreted_log_output += '\n'

            if self.reevaluation_expired:
                interpreted_log_output += app_object.generate_win32app_first_line_log_output()
                temp_log, processing_stop = app_object.generate_win32app_pre_download_log_output()
                interpreted_log_output += temp_log
                interpreted_log_output += '\n'
                interpreted_log_output += 'Processing dependent apps start\n\n'

            dependency_app_id_list = [each_dependency_dic['ChildId'] for each_dependency_dic in app_object.dependent_apps_list]
            dependency_app_object_list = [each_app for each_app in self.win32app_object_list if each_app.app_id in dependency_app_id_list]

            for each_app_object in dependency_app_object_list:
                app_index = app_index + 1
                interpreted_log_output += self.generate_subgraph_dependent_app_processing_log_output(each_app_object, app_index)

            if self.reevaluation_expired:
                interpreted_log_output += 'All dependent apps processed, processing root app [' + app_object.app_name + ']\n\n'
                if processing_stop:
                    interpreted_log_output += "No action required for this app"
                else:
                    interpreted_log_output += app_object.generate_win32app_post_download_log_output()
            else:
                pass

            # if each_app_object.app_id not in self.actual_app_id_to_install_list:
            #     # interpreted_log_output += each_app_object.generate_win32app_first_part_log_output()
            #     interpreted_log_output += '\n'
            #     interpreted_log_output += (each_app_object.pre_install_detection_time
            #                                + ' Effective intent: ' + each_app_object.effective_intent + '\n')
            # else:
            #     interpreted_log_output += self.generate_subgraph_dependent_app_processing_log_output(each_app_object, app_index + 1)
            #     interpreted_log_output += '\n'
            #
            # if app_object.app_id in self.actual_app_id_to_install_list and not app_object.pre_install_detection:
            #     interpreted_log_output += 'All dependent apps proccessed, processing app [' + app_object.app_name +']\n\n'
            #     interpreted_log_output += app_object.generate_win32app_post_download_log_output()

        return interpreted_log_output

    def generate_subgraph_log_output(self):
        interpreted_log_output = ""

        if self.is_stand_alone_subgraph:
            if len(self.win32app_object_list) == 1:
                # Add subgraph meta to log
                """
                The first app in the line below is not necessarily the root app.
<![LOG[[Win32App][V3Processor] Processing subgraph with app ids: 1f4b773e-53ed-4cd8-b12b-16c336bba549, b3aa3d56-d0f5-47a0-8240-ae85ed050a6b, 3dde4e19-3a18-4dec-b60e-720b919e1790]LOG]
                """
                interpreted_log_output += self.win32app_object_list[0].generate_standalone_win32_app_meta_log_output()
                interpreted_log_output += '\n'
                if not self.reevaluation_expired:
                    interpreted_log_output += "Subgraph will be reevaluated after last reevaluation time + 8 hours\n\n"
                    return interpreted_log_output
                else:
                    # Add subgraph processing log
                    interpreted_log_output += self.win32app_object_list[0].generate_standalone_win32app_log_output()
                    interpreted_log_output += '\n'
            else:
                print("Error in code. Standalone flow does not have 1 app in current subgraph!")
        else:
            if (len(self.win32app_object_list)) > 0:
                if (len(self.win32app_object_list)) > 1:
                    self.win32app_object_list[0].is_root_app = True
                app_index = 1
                interpreted_log_output += (
                    self.generate_subgraph_dependent_app_processing_log_output(self.win32app_object_list[0], app_index))
                interpreted_log_output += '\n'

            interpreted_log_output += '\n'
            if not self.reevaluation_expired:
                interpreted_log_output += "Subgraph will be reevaluated after last reevaluation time + 8 hours\n\n"
                return interpreted_log_output
            """
            If SubGraph reevaluation expired, it will process all inside apps' detection results and applicability.
            First output the last_enforcement_state for all apps in this subgraph
            Then If app in GRS, output detection only status

            If SubGraph has dependency, targeted app will not process to download and install if any of the dependent app 
            is not detected and not targeted(by direct assignment or dependent auto install)

            Assuming that first app_id in
            <![LOG[[Win32App][V3Processor] Processing subgraph with app ids: b3aa3d56-d0f5-47a0-8240-ae85ed050a6b, 3dde4e19-3a18-4dec-b60e-720b919e1790, 1f4b773e-53ed-4cd8-b12b-16c336bba549]LOG]!>
            is always the root app id in this subgraph

            """

        return interpreted_log_output
