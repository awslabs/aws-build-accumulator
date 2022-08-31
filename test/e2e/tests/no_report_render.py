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

SLOW = False


def get_init_args():
    return {
        "kwargs": {
            "project": "test_no_report_render",
        }
    }


def get_jobs():
    jobs = []
    jobs.append({
        "kwargs": {
            "command": "/usr/bin/false",
            "ci-stage": "build",
            "pipeline": "job fails",
        }
    })
    jobs.append({
        "kwargs": {
            "command": "/usr/bin/true",
            "ci-stage": "build",
            "pipeline": "job succeeds",
        }
    })
    return jobs


def get_run_build_args():
    return {
        "args": [
            "no-report-render",
        ]
    }


def check_run(run):
    return True


def check_no_report_render():
    return True
