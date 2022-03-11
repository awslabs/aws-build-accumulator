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
# permissions and limitations under the License

import json
import logging
import os
import sys
import uuid

from lib import litani


_PRIVATE_JOB_FIELDS = ("job_id", "status_file", "subcommand")

async def add_job(job_dict):
    cache_file = litani.get_cache_dir() / litani.CACHE_FILE
    with open(cache_file) as handle:
        cache_contents = json.load(handle)
    if job_dict["ci_stage"] not in cache_contents["stages"]:
        valid_stages = "', '".join(cache_contents["stages"])
        logging.error(
            "Invalid stage name '%s' was provided, possible "
            "stage names are: '%s'", job_dict["ci_stage"], valid_stages)
        sys.exit(1)

    jobs_dir = litani.get_cache_dir() / litani.JOBS_DIR
    jobs_dir.mkdir(exist_ok=True, parents=True)

    if job_dict["phony_outputs"]:
        if not job_dict["outputs"]:
            job_dict["outputs"] = job_dict["phony_outputs"]
        else:
            for phony_output in job_dict["phony_outputs"]:
                if phony_output not in job_dict["outputs"]:
                    job_dict["outputs"].append(phony_output)

    if "func" in job_dict:
        job_dict.pop("func")

    job_id = str(uuid.uuid4())
    job_dict["job_id"] = job_id
    job_dict["status_file"] = str(
        litani.get_status_dir() / ("%s.json" % job_id))

    logging.debug("Adding job: %s", json.dumps(job_dict, indent=2))

    for key in _PRIVATE_JOB_FIELDS:
        if key not in job_dict:
            raise AssertionError(f"Key {key} missing from job definition")

    with litani.atomic_write(jobs_dir / ("%s.json" % job_id)) as handle:
        print(json.dumps(job_dict, indent=2), file=handle)


async def get_jobs():
    out = []
    jobs_dir = litani.get_cache_dir() / litani.JOBS_DIR

    if not jobs_dir.exists():
        logging.warning("No jobs have been added")
        return out

    for job in jobs_dir.iterdir():
        with open(job) as handle:
            job_dict = json.load(handle)
            for key in _PRIVATE_JOB_FIELDS:
                job_dict.pop(key)
            out.append(job_dict)
    return out


async def print_jobs(args=None):
    jobs = await get_jobs()

    out_file = sys.stdout
    if args and args.out_file:
        out_file = args.out_file

    print(json.dumps(jobs, indent=2), file=out_file)

    # sys.stdout.close() only closes the python file object, but the underlying
    # file handle in the C stdlib would remain open, so this is how we need to
    # close it for transform_jobs
    sys.stdout.flush()
    os.close(sys.stdout.fileno())
