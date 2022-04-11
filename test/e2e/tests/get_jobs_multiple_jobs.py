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
import logging
import sys


SLOW = False


def get_init_args():
    return {
        "kwargs": {
            "project": "foo",
        }
    }


def get_jobs():
    return [{
        "kwargs": {
            "command": "echo foo",
            "ci-stage": "build",
            "pipeline": "foo",
        }
    }, {
        "kwargs": {
            "command": "echo bar",
            "ci-stage": "build",
            "pipeline": "foo",
        }
    }, {
        "kwargs": {
            "command": "echo baz",
            "ci-stage": "build",
            "pipeline": "foo"
        }
    }]


def get_check_get_jobs_args():
    return {}



def check_get_jobs(jobs_json):
    jobs = json.loads(jobs_json)
    if len(jobs) != 3:
        logging.error("Expected to get 3 job, got %s", len(jobs))
        return False

    expected_commands = {
        "echo bar",
        "echo baz",
        "echo foo",
    }
    actual_commands = set([j["command"] for j in jobs])
    if actual_commands != expected_commands:
        logging.error("Expected job commands to be %s, actual %s",
                expected_commands,
                actual_commands)
        return False
    return True


def get_post_check_jobs():
    return []


def get_run_build_args():
    return {}


def check_run(run):
    return len(run["pipelines"][0]["ci_stages"][0]["jobs"]) == 3
