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
PHONY_ADD_JOBS = True


def get_init_args():
    return {
        "kwargs": {
            "project": "foo",
        }
    }


def get_jobs():
    return []


def get_set_jobs_args():
    jobs = [{
            "command": "echo foo",
            "pipeline_name": "foo",
            "ci_stage": "build",
    }, {
            "command": "echo baz",
            "pipeline_name": "foo",
            "ci_stage": "build",
    }, {
            "command": "echo bar",
            "pipeline_name": "foo",
            "ci_stage": "build",
    }]
    return {
        "kwargs": {
            "from_string": json.dumps(jobs)
        }
    }


def get_run_build_args():
    return {}


def check_run(run):
    jobs = run["pipelines"][0]["ci_stages"][0]["jobs"]

    expected_outputs = ["foo", "bar", "baz"]
    for job in jobs:
        expected_outputs.remove(job["stdout"][0].strip())

    return all((
        len(jobs) == 3,
        expected_outputs == [],
    ))
