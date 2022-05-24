# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

import json


def get_summary(run_dict):
    # The list of possible statuses can be viewed in the man page for run.json
    status_summary_map = {}
    pipeline_status_map = {}
    for pipeline in run_dict["pipelines"]:
        status_name_pretty = pipeline["status"].title().replace("_", " ")
        try:
            status_summary_map[status_name_pretty] += 1
        except KeyError:
            status_summary_map[status_name_pretty] = 1
        pipeline_status_map[pipeline["name"]] = status_name_pretty
    return json.dumps({
        "Breakdown of statuses across pipelines": status_summary_map,
        "Breakdown of status per pipeline": pipeline_status_map}, indent=2)


def summarize_results(run_dict):
    print(get_summary(run_dict))
