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


SLOW = False

EXPECTED_JOB = {
    "command": "echo foo",
    "ci-stage": "build",
    "pipeline": "foo",
}


def get_init_args():
    return {
        "kwargs": {
            "project": "foo",
        }
    }


def get_jobs():
    return [{"kwargs": EXPECTED_JOB}]


def get_check_get_jobs_args():
    return {}


def check_get_jobs(jobs_json):
    jobs = json.loads(jobs_json)
    print(json.dumps(jobs, indent=2))
    if len(jobs) != 1:
        logging.error("Expected to get 1 job, got %s", len(jobs))
        return False

    job = jobs[0]
    for key in EXPECTED_JOB.keys():
        if job.get(key) != EXPECTED_JOB[key]:
            logging.error(
                "Expected job to have key-value pair '%s': '%s'",
                key, EXPECTED_JOB[key])
            return False

    removed_keys = [
        "job_id",
        "status_file",
        "subcommand",
    ]
    for key in removed_keys:
        if key in job:
            logging.error("Expected key %s to be removed from job output", key)
            return False
    return True


def get_post_check_jobs():
    return []


def get_run_build_args():
    return {}


def check_run(run):
    job = run["pipelines"][0]["ci_stages"][0]["jobs"][0]
    return job["stdout"][0].strip() == "foo"
