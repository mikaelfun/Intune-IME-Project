import logprocessinglibrary


class PowerShellObject:
    def __init__(self, ime_log, policy_json, agent_executor_log):
        self.log_keyword_table = logprocessinglibrary.init_keyword_table()
        self.log_content = ime_log
        self.policy_json = policy_json
        self.agent_executor_log = agent_executor_log
        self.log_len = len(self.log_content)
        if self.log_len < 3 or len(self.log_content[0]) < 9:
            print("Warning PS.self.log_len < 3! Exit 3101")
            # return None
            # exit(3101)
        self.poller_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])[:-4]
        self.start_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[0])
        self.stop_time = logprocessinglibrary.get_timestamp_by_line(self.log_content[-1])
        self.esp_phase = ""
        self.user_session = ""
        self.poller_apps_got = '0'
        self.comanagement_workload = ""
        self.app_type = ""
        self.is_throttled = False
        self.sub_graph_list = []
        self.expired_sub_graph_list = []  # Expired subgraph list
        self.sub_graph_reevaluation_time_list = dict()
        self.poller_reevaluation_check_in_time = ""
        self.get_policy_json = {}
        self.subgraph_num_expected = -1
        self.subgraph_num_actual = -1
        self.expired_subgraph_num_actual = 0
        self.index_list_subgraph_processing_start = []
        self.index_list_subgraph_processing_stop = []
        self.last_enforcement_json_dict = dict()
