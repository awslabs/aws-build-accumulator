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

import argparse
import json
import logging
import os
import re
import sys
import uuid

from lib import litani


_PRIVATE_JOB_FIELDS = ("job_id", "status_file", "subcommand")

def get_add_job_args():
    return [(
        "describing the build graph", [{
            "flags": ["--inputs"],
            "nargs": "+",
            "metavar": "F",
            "help": "list of inputs that this job depends on",
        }, {
            "flags": ["--command"],
            "metavar": "C",
            "required": True,
            "help": "the command to run once all dependencies are satisfied",
        }, {
            "flags": ["--outputs"],
            "metavar": "F",
            "nargs": "+",
            "help": "list of outputs that this job generates",
        }]), (
        "job control", [{
            "flags": ["--pipeline-name"],
            "required": True,
            "metavar": "P",
            "help": "which pipeline this job is a member of",
        }, {
            "flags": ["--ci-stage"],
            "required": True,
            "metavar": "S",
            "help": "which CI stage this job should execute in. "
        }, {
            "flags": ["--cwd"],
            "metavar": "DIR",
            "help": "directory that this job should execute in"
        }, {
            "flags": ["--timeout"],
            "metavar": "N",
            "type": int,
            "help": "max number of seconds this job should run for"
        }, {
            "flags": ["--timeout-ok"],
            "action": "store_true",
            "help": "if the job times out, terminate it and return success"
        }, {
            "flags": ["--timeout-ignore"],
            "action": "store_true",
            "help": "if the job times out, terminate it continue, but "
                    "fail at the end",
        }, {
            "flags": ["--ignore-returns"],
            "metavar": "RC",
            "nargs": "+",
            "help": "if the job exits with one of the listed return codes, "
                    "return success"
        }, {
            "flags": ["--ok-returns"],
            "metavar": "RC",
            "nargs": "+",
            "help": "if the job exits with one of the listed return codes, "
                    "continue the build but fail at the end"
        }, {
            "flags": ["--outcome-table"],
            "metavar": "F",
            "help": "path to a JSON outcome table that determines the outcome "
                    "of this job"
        }, {
            "flags": ["--interleave-stdout-stderr"],
            "action": "store_true",
            "help": "simulate '2>&1 >...'"
        }, {
            "flags": ["--stdout-file"],
            "metavar": "FILE",
            "help": "file to redirect stdout to"
        }, {
            "flags": ["--stderr-file"],
            "metavar": "FILE",
            "help": "file to redirect stderr to"
        }, {
            "flags": ["--pool"],
            "metavar": "NAME",
            "help": "pool to which this job should be added"
        }]), (
        "misc", [{
            "flags": ["--description"],
            "metavar": "DESC",
            "help": "string to print when this job is being run",
        }, {
            "flags": ["--profile-memory"],
            "action": "store_true",
            "default": False,
            "help": "profile the memory usage of this job"
        }, {
            "flags": ["--profile-memory-interval"],
            "metavar": "N",
            "default": 10,
            "type": int,
            "help": "seconds between memory profile polls"
        }, {
            "flags": ["--phony-outputs"],
            "metavar": "OUT",
            "nargs": "*",
            "help": "do not warn if OUT does not exist upon job completion"
        }, {
            "flags": ["--tags"],
            "metavar": "TAG",
            "nargs": "+",
            "help": "a list of tags for this job"
        }]),
    ]


def configure_args(**kwargs):
    cmd = []
    for arg, value in kwargs.items():
        switch = f"--{re.sub('_', '-', arg)}"
        if value is None:
            continue
        if isinstance(value, bool):
            if value:
                cmd.append(switch)
            continue

        cmd.append(switch)
        if isinstance(value, list):
            cmd.extend(str(v) for v in value)
        else:
            cmd.append(str(value))
    return cmd


def fill_job(job):
    parser = argparse.ArgumentParser()
    for group_name, args in get_add_job_args():
        group = parser.add_argument_group(title=group_name)
        for arg in args:
            flags = arg.pop("flags")
            group.add_argument(*flags, **arg)
    args = configure_args(**job)
    job_dict = vars(parser.parse_known_args(args)[0])
    for key in job:
        if key not in job_dict:
            job_dict[key] = job[key]
    return job_dict


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


def _delete_jobs():
    jobs_dir = litani.get_cache_dir() / litani.JOBS_DIR

    try:
        for job_file in jobs_dir.iterdir():
            os.unlink(job_file)
    except FileNotFoundError:
        pass


async def set_jobs(job_list):
    _delete_jobs()
    for job in job_list:
        filled_job = fill_job(job)
        filled_job["subcommand"] = "add-job"
        await add_job(filled_job)


def _read_jobs():
    in_text = sys.stdin.read()
    try:
        jobs = json.loads(in_text)
    except json.JSONDecodeError:
        logging.error("Could not read jobs due to malformatted JSON")
        sys.exit(1)
    return jobs


async def transform_jobs(_):
    await print_jobs()
    new_jobs = _read_jobs()
    await set_jobs(new_jobs)
