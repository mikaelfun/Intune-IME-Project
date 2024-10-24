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
import logprocessinglibrary
import win32app
import constructinterpretedlog


class SubGraph:
    def __init__(self, subgraph_processing_log, policy_json, last_enforcement_json_dict, reevaluation_time="Subgraph Not Evaluated before"):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.reevaluation_time = reevaluation_time
        self.reevaluation_expired = True
        self.hash_key = ""
        self.grs_time_list = dict()  # key: app id string, value: grs time string
        self.grs_expiry = dict()  # key: app id string, value: true(expired), false(not expired)
        self.app_num = 0
        self.log_content = subgraph_processing_log
        self.log_len = len(self.log_content)
        self.app_id_list = []
        self.root_app_list = []
        self.app_names = dict()  # key: app id string, value: app name string
        self.policy_json = policy_json
        self.subgraph_app_object_list = []
        """
                subgraph_type
                1: standalone
                2: dependency
                3: supercedence
                """
        self.subgraph_type = 1
        self.is_supercedence = False
        self.last_enforcement_json_dict = last_enforcement_json_dict  # key: app id string, value: last_enforcement_json
        """ 
        <![LOG[[Win32App][ActionProcessor] Found: 1 apps with intent to install: [1f4b773e-53ed-4cd8-b12b-16c336bba549].]LOG]
        After dependency apps targeting evaluation, it will be reflected in this line to check whether each app should be processed.
        If not processed, it means some dependent app is not targeted or dependent app itself is not targeted
        """
        if self.log_len < 2:
            print("Error creating SubGraph Object!")
            print(subgraph_processing_log)
            return None
        self.process_subgraph_meta()
        self.get_app_name_from_json_by_app_id()
        self.initialize_win32_apps_list()

    def check_subgraph_type(self):
        for each_app_id in self.app_id_list:
            cur_app_dict = self.find_app_dict_json_from_policy_json(each_app_id)
            cur_app_dependent_apps_list = cur_app_dict['FlatDependencies']
            """
            [{"Action":10,"AppId":"b3aa3d56-d0f5-47a0-8240-ae85ed050a6b","ChildId":"3dde4e19-3a18-4dec-b60e-720b919e1790","Type":0,"Level":0},{"Action":0,"AppId":"b3aa3d56-d0f5-47a0-8240-ae85ed050a6b","ChildId":"1f4b773e-53ed-4cd8-b12b-16c336bba549","Type":0,"Level":0}]
            """
            if cur_app_dependent_apps_list:
                for each_dependency_relationship_dict in cur_app_dependent_apps_list:
                    """
                    public enum DependencyAction
                    {
                        Detect = 0,
                        Install = 10,
                    }

                    public enum SupersedenceAction
                    {
                        Update = 100,
                        Replace = 110
                    }
                    """
                    if each_dependency_relationship_dict["Action"] > 10:
                        self.subgraph_type = 3
                        return None
                    elif each_dependency_relationship_dict["Action"] <= 10:
                        self.subgraph_type = 2

    def get_app_name_from_json_by_app_id(self):
        for cur_app_index in range(self.app_num):
            cur_app_name = [match['Name'] for match in self.policy_json if match['Id'] == self.app_id_list[cur_app_index]].pop()
            self.app_names[self.app_id_list[cur_app_index]] = cur_app_name
            # print(cur_app_name)

    def find_app_dict_json_from_policy_json(self, app_id):
        cur_app_dict = {}
        for each_dic in self.policy_json:
            if each_dic['Id'] == app_id:
                cur_app_dict = each_dic
                break
        if not cur_app_dict:
            print("Fatal! Win32App not found in get policy json!")
            return None
        return cur_app_dict

    def sort_app_id_list_top_root_app(self):
        """
        Defining a dictionary of app ids, loop through all app ids and FlatDependencies to insert to dictionary
        key: each app id
        value: all of its root apps ids

        In one subgraph, the top root app is an app without any root apps above it.
        So it is the app not found in the dictionary

        There could be multiple root apps in 1 subgraph. Eg. app1 depends on app2. app3 depends on app2. Then both app1
        and app3 are root apps, and 3 apps are included in 1 subgraph.
        The install sequence would be app2->app1->app2->app3

        :return: None
        """
        root_id = ""
        leaf_to_root_dic = {}
        root_to_leaf_dic = {}
        new_app_id_list = []
        for each_app_id in self.app_id_list:
            cur_app_dict = self.find_app_dict_json_from_policy_json(each_app_id)
            cur_app_dependent_apps_list = cur_app_dict['FlatDependencies']
            """
            [{"Action":10,"AppId":"b3aa3d56-d0f5-47a0-8240-ae85ed050a6b","ChildId":"3dde4e19-3a18-4dec-b60e-720b919e1790","Type":0,"Level":0},{"Action":0,"AppId":"b3aa3d56-d0f5-47a0-8240-ae85ed050a6b","ChildId":"1f4b773e-53ed-4cd8-b12b-16c336bba549","Type":0,"Level":0}]
            """
            if cur_app_dependent_apps_list:
                for each_dependency_relationship_dict in cur_app_dependent_apps_list:
                    # each_dependency_relationship_json = json.loads(each_dependency_relationship_string)
                    if each_dependency_relationship_dict["ChildId"] in leaf_to_root_dic.keys():
                        leaf_to_root_dic[each_dependency_relationship_dict["ChildId"]].append(each_app_id)
                    else:
                        leaf_to_root_dic[each_dependency_relationship_dict["ChildId"]] = [each_app_id]
                    if each_app_id in root_to_leaf_dic.keys():
                        root_to_leaf_dic[each_app_id].append(each_dependency_relationship_dict["ChildId"])
                    else:
                        root_to_leaf_dic[each_app_id] = [each_dependency_relationship_dict["ChildId"]]

        for each_app_id in self.app_id_list:
            if each_app_id not in leaf_to_root_dic.keys():
                self.root_app_list.append(each_app_id)
                # self.app_id_list.remove(each_app_id)
                # self.app_id_list.insert(0, each_app_id)
        for each_root in self.root_app_list:
            new_app_id_list += (x for x in self.recursive_add_dependent_app_id(each_root, root_to_leaf_dic) if x not in new_app_id_list)

        self.app_id_list = new_app_id_list

    # depth first list to format list of all dependent apps
    def recursive_add_dependent_app_id(self, app_id, root_to_leaf_dic):
        if app_id not in root_to_leaf_dic:
            return [app_id]
        else:
            temp_list = [app_id]
            for each_leaf_app in root_to_leaf_dic[app_id]:
                """
                Fix issue with double dependency
                """
                temp_result = self.recursive_add_dependent_app_id(each_leaf_app, root_to_leaf_dic)
                temp_list += [each_id for each_id in temp_result if each_id not in temp_list]
            return temp_list

    def process_subgraph_meta(self):
        id_start_index = len(self.log_keyword_table['LOG_SUBGRAPH_PROCESSING_START_INDICATOR'])
        id_stop_index = self.log_content[0].find(self.log_keyword_table['LOG_ENDING_STRING'])
        """
        Need to put the root app of dependency chain in first one.
        """
        self.app_id_list = list(
            (self.log_content[0][id_start_index:id_stop_index]).split(', '))
        # print(cur_subgraph.app_id_list)
        self.app_num = len(self.app_id_list)

        self.check_subgraph_type()

        if self.subgraph_type >= 2:
            self.sort_app_id_list_top_root_app()
        for each_line_index in range(1, self.log_len):
            cur_line = self.log_content[each_line_index]
            if cur_line.startswith(self.log_keyword_table['LOG_WIN32_GRS_INDICATOR']):
                # app was processed before, saving hash key, grs time,
                """
                <![LOG[[Win32App][GRSManager] Found GRS value: 03/23/2023 08:55:35 at key 8679bddf-b85f-473c-bc47-2ed0457ec9fb\GRS\2BKBFKBaevJ8qnbQsLVnCKDoI1ZjfmU5sTdZPc/QtWE=\cce28372-03a1-4006-8035-00deb0c906ed.]LOG]!>
                """
                grs_value_hash_index_start = len(self.log_keyword_table['LOG_WIN32_GRS_INDICATOR']) + len('03/23/2023 08:55:35 at key 8679bddf-b85f-473c-bc47-2ed0457ec9fb\GRS') + 1
                grs_value_hash_index_end = grs_value_hash_index_start + logprocessinglibrary.CONST_GRS_HASH_KEY_LEN
                if self.hash_key == "":
                    self.hash_key = cur_line[grs_value_hash_index_start:grs_value_hash_index_end]
                app_id_index_end = cur_line.find(self.log_keyword_table['LOG_ENDING_STRING']) - 1
                app_id_index_start = app_id_index_end - logprocessinglibrary.CONST_APP_ID_LEN
                cur_app_id = cur_line[app_id_index_start:app_id_index_end]
                grs_time_index_start = len(self.log_keyword_table['LOG_WIN32_GRS_INDICATOR'])
                log_subgraph_hash_indicator = ' at key '
                grs_time_index_end = cur_line.find(log_subgraph_hash_indicator)
                cur_app_grs_time = cur_line[grs_time_index_start:grs_time_index_end]
                self.grs_time_list[cur_app_id] = cur_app_grs_time
                # print(self.hash_key)
            elif cur_line.startswith(self.log_keyword_table['LOG_WIN32_NO_GRS_1_INDICATOR']):
                cur_app_id = logprocessinglibrary.find_app_id_with_starting_string(cur_line, self.log_keyword_table['LOG_WIN32_NO_GRS_1_INDICATOR'])
                # print(cur_line[79:83])
                if self.log_keyword_table['LOG_WIN32_NO_GRS_2_INDICATOR'] in cur_line:
                    # app has no grs found.
                    """
                    <![LOG[[Win32App][GRSManager] App with id: 471f61b1-58ad-431b-bd4d-386d3c953773 has no recorded GRS value which will be treated as expired. | Hash = Z/qdb2IBJPXgSPPxMV14feLXHs7e8XnvSEYNW5fqv3M=]LOG]!
                    """
                    grs_value_hash_index_start = len('<![LOG[[Win32App][GRSManager] App with id: ') + logprocessinglibrary.CONST_APP_ID_LEN + len(' has no recorded GRS value which will be treated as expired. | Hash = ')
                    grs_value_hash_index_end = grs_value_hash_index_start + logprocessinglibrary.CONST_GRS_HASH_KEY_LEN
                    if self.hash_key == "":
                        self.hash_key = cur_line[grs_value_hash_index_start:grs_value_hash_index_end]
                    self.grs_expiry[cur_app_id] = True
                elif cur_line[len(self.log_keyword_table['LOG_WIN32_NO_GRS_1_INDICATOR']) + logprocessinglibrary.CONST_APP_ID_LEN: len(self.log_keyword_table['LOG_WIN32_NO_GRS_1_INDICATOR']) + logprocessinglibrary.CONST_APP_ID_LEN + len(' is ')] == ' is ':
                    """
                    <![LOG[[Win32App][GRSManager] App with id: cce28372-03a1-4006-8035-00deb0c906ed is expired. | Hash = 2BKBFKBaevJ8qnbQsLVnCKDoI1ZjfmU5sTdZPc/QtWE=
                    """
                    expiry_start_index = len(self.log_keyword_table['LOG_WIN32_NO_GRS_1_INDICATOR']) + logprocessinglibrary.CONST_APP_ID_LEN + len(' is ')
                    expiry_end_index = cur_line.find('. | Hash =')
                    cur_app_expiry_string = cur_line[expiry_start_index: expiry_end_index]
                    """
                    Available app will skip GRS:
                    
                    <![LOG[[Win32App][GRSManager] App with id: 2c675442-fd92-4000-ab65-e740d6187efe is not expired but will be enforced due to targeting intent on the subgraph. | Hash = JEJN8M6SCgv6ZxH2rSNO0aC3ZzY2X2yblciKmvFz3Q4=
                    """
                    if cur_app_expiry_string == 'expired':
                        self.grs_expiry[cur_app_id] = True
                    elif cur_app_expiry_string == 'not expired':
                        self.grs_expiry[cur_app_id] = False
                    elif cur_app_expiry_string == 'not expired but will be enforced due to targeting intent on the subgraph':
                        self.grs_expiry[cur_app_id] = True

            elif cur_line.startswith(self.log_keyword_table['LOG_SUBGRAPH_NOT_EXPIRED_INDICATOR']):
                # meaning the current subgraph will not be processed
                self.reevaluation_expired = False

    def initialize_win32_apps_list(self):
        for cur_app_index in range(self.app_num):
            cur_app_id = self.app_id_list[cur_app_index]
            # if cur_app_id == "545d5b9c-60e4-488d-a084-9896ba3b3d6e":
            #     print("debug")
            cur_app_name = self.app_names[cur_app_id] if cur_app_id in self.app_names.keys() else ''
            cur_app_grs_time = self.grs_time_list[cur_app_id] if cur_app_id in self.grs_time_list.keys() else ''
            cur_app_grs_expiry = self.grs_expiry[cur_app_id] if cur_app_id in self.grs_expiry.keys() else False
            cur_app_last_enforcement_json = self.last_enforcement_json_dict[cur_app_id] \
                if cur_app_id in self.last_enforcement_json_dict.keys() else None

            cur_win32_app_object = win32app.Win32App(self.log_content, cur_app_id, cur_app_name, self.policy_json,
                                                          cur_app_grs_time, self.hash_key, cur_app_grs_expiry,
                                                          self.subgraph_type, cur_app_last_enforcement_json)
            if cur_app_id in self.root_app_list:
                cur_win32_app_object.is_root_app = True
            self.subgraph_app_object_list.append(cur_win32_app_object)
            # print("here")

    def get_subgraph_object_by_id(self, app_id):
        for each_subgraph_app_object in self.subgraph_app_object_list:
            if each_subgraph_app_object.app_id == app_id:
                return each_subgraph_app_object
        return None

    # Recursive function to handle dependency chain
    def generate_subgraph_dependent_app_processing_log_output(self, app_object, depth=0):
        interpreted_log_output = ""
        # interpreted_log_output += write_log_output_line_with_indent_depth(str(app_index) + '.\n', depth)
        has_dependent_apps = True if app_object.dependent_apps_list is not None else False
        if not has_dependent_apps:
            interpreted_log_output += app_object.generate_standalone_win32_app_meta_log_output(depth)
            interpreted_log_output += '\n'
            if self.reevaluation_expired:
                interpreted_log_output += app_object.generate_standalone_win32app_log_output(depth)
                interpreted_log_output += '\n'
        else:
            interpreted_log_output += app_object.generate_dependency_win32_app_meta_log_output(depth)
            interpreted_log_output += '\n'

            if self.reevaluation_expired:
                interpreted_log_output += app_object.generate_win32app_first_line_log_output(depth)
                interpreted_log_output += app_object.generate_win32app_pre_download_log_output(depth)
                interpreted_log_output += '\n'
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(app_object.pre_install_detection_time + ' Processing dependent apps start\n\n', depth)

            dependency_app_id_list = [each_dependency_dic['ChildId'] for each_dependency_dic in app_object.dependent_apps_list]
            dependency_app_object_list = [each_app for each_app in self.subgraph_app_object_list if each_app.app_id in dependency_app_id_list]

            each_app_object = None
            for each_app_object in dependency_app_object_list:
                interpreted_log_output += self.generate_subgraph_dependent_app_processing_log_output(each_app_object, depth + 1)
                interpreted_log_output += '\n'

            if self.reevaluation_expired:
                dependent_app_end_time = each_app_object.end_time
                if not each_app_object.has_enforcement:
                    dependent_app_end_time = each_app_object.applicability_time
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(dependent_app_end_time + ' All dependent apps processed, processing root app [' + app_object.app_name + ']\n\n', depth)
                interpreted_log_output += app_object.generate_win32app_post_download_log_output(depth)
                if not app_object.has_enforcement and not app_object.reason_need_output:
                    interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(app_object.end_time + ' No Action required for this root app [' + app_object.app_name + '] because ' + app_object.no_enforcement_reason + '\n', depth)

            else:
                pass

        return interpreted_log_output

    # For loop function to handle supersedence chain
    def generate_subgraph_supersedence_app_processing_log_output(self, app_object, depth=0):
        interpreted_log_output = ""
        # interpreted_log_output += write_log_output_line_with_indent_depth(str(app_index) + '.\n', depth)
        has_supersedence_apps = True if app_object.supersedence_apps_list is not None else False
        if not has_supersedence_apps:
            interpreted_log_output += app_object.generate_standalone_win32_app_meta_log_output(depth)
            interpreted_log_output += '\n'
            if self.reevaluation_expired:
                interpreted_log_output += app_object.generate_standalone_win32app_log_output(depth)
                interpreted_log_output += '\n'
        else:
            interpreted_log_output += app_object.generate_supercedence_win32_app_meta_log_output(depth)
            interpreted_log_output += '\n'

            if self.reevaluation_expired:
                interpreted_log_output += app_object.generate_win32app_first_line_log_output(depth)
                interpreted_log_output += app_object.generate_win32app_pre_download_log_output(depth)
                interpreted_log_output += '\n'
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    app_object.pre_install_detection_time + ' Processing superceded apps start\n\n', depth)

            supersedence_app_id_list = [each_supersedence_dic['ChildId'] for each_supersedence_dic in
                                      app_object.supersedence_apps_list]
            supersedence_app_object_list = [each_app for each_app in self.subgraph_app_object_list if
                                          each_app.app_id in supersedence_app_id_list]

            each_app_object = None
            for each_app_object in supersedence_app_object_list:
                interpreted_log_output += self.generate_subgraph_supersedence_app_processing_log_output(
                    each_app_object, depth + 1)
                interpreted_log_output += '\n'

            if self.reevaluation_expired:
                superseded_app_end_time = each_app_object.end_time
                if not each_app_object.has_enforcement:
                    superseded_app_end_time = each_app_object.applicability_time
                interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                    superseded_app_end_time + ' All superseded apps processed, processing superceding app [' + app_object.app_name + ']\n\n',
                    depth)
                interpreted_log_output += app_object.generate_win32app_post_download_log_output(depth)
                if not app_object.has_enforcement and not app_object.reason_need_output:
                    interpreted_log_output += constructinterpretedlog.write_log_output_line_with_indent_depth(
                        app_object.end_time + ' No Action required for this root app [' + app_object.app_name + '] because ' + app_object.no_enforcement_reason + '\n',
                        depth)

            else:
                pass

        return interpreted_log_output

    def generate_subgraph_log_output(self):
        interpreted_log_output = ""

        if self.subgraph_type == 1:
            if len(self.subgraph_app_object_list) == 1:
                # Check if Win32 or MSFB
                if self.subgraph_app_object_list[0].app_type == "Win32":
                    # Add subgraph meta to log
                    interpreted_log_output += self.subgraph_app_object_list[0].generate_standalone_win32_app_meta_log_output()
                    interpreted_log_output += '\n'
                    if not self.reevaluation_expired:
                        interpreted_log_output += "Subgraph will be reevaluated after last reevaluation time + 8 hours\n\n"
                        return interpreted_log_output
                    else:
                        # Add subgraph processing log
                        interpreted_log_output += self.subgraph_app_object_list[0].generate_standalone_win32app_log_output()
                        interpreted_log_output += '\n'
                elif self.subgraph_app_object_list[0].app_type == "MSFB":
                    # Add subgraph meta to log
                    interpreted_log_output += self.subgraph_app_object_list[
                        0].generate_msfb_app_meta_log_output()
                    interpreted_log_output += '\n'
                    if not self.reevaluation_expired:
                        interpreted_log_output += "Subgraph will be reevaluated after last reevaluation time + 8 hours\n\n"
                        return interpreted_log_output
                    else:
                        # Add subgraph processing log
                        interpreted_log_output += self.subgraph_app_object_list[0].generate_msfb_log_output()
                        interpreted_log_output += '\n'
            else:
                print("Error in code. Standalone flow does not have 1 app in current subgraph!")
        elif self.subgraph_type == 2:
            if (len(self.subgraph_app_object_list)) > 0:
                for each_root in self.root_app_list:
                    each_root_win32_object = self.get_subgraph_object_by_id(each_root)
                    interpreted_log_output += (
                        self.generate_subgraph_dependent_app_processing_log_output(each_root_win32_object))
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
        elif self.subgraph_type == 3:
            """
            supersedence flow
            """
            if (len(self.subgraph_app_object_list)) > 0:
                for each_root in self.root_app_list:
                    each_root_win32_object = self.get_subgraph_object_by_id(each_root)
                    interpreted_log_output += (
                        self.generate_subgraph_supersedence_app_processing_log_output(each_root_win32_object))
                    interpreted_log_output += '\n'

            interpreted_log_output += '\n'
            if not self.reevaluation_expired:
                interpreted_log_output += "Subgraph will be reevaluated after last reevaluation time + 8 hours\n\n"
                return interpreted_log_output
        else:
            print("subgraph_type unknown!")
        return interpreted_log_output
