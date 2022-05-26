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

import __main__

import json
import logging
import os
import pathlib
import shutil
import shlex
import sys

from lib import litani
import lib.jobs
import lib.output_artifact
import lib.util


def get_exec_job_args():
    exec_job_args = list(lib.jobs.get_add_job_args())
    exec_job_args.append((
        "`litani exec`-specific flags", [{
            "flags": ["--status-file"],
            "metavar": "F",
            "required": True,
            "help": "JSON file to write command status to",
    }, {
            "flags": ["--job-id"],
            "metavar": "ID",
            "required": True,
            "help": "the globally unique job ID",
    }]))
    return exec_job_args


def add_subparser(subparsers):
    exec_job_pars = subparsers.add_parser("exec")
    exec_job_pars.set_defaults(func=exec_job)
    for group_name, args in get_exec_job_args():
        group = exec_job_pars.add_argument_group(title=group_name)
        for arg in args:
            flags = arg.pop("flags")
            group.add_argument(*flags, **arg)


def make_litani_exec_command(add_args):
    cmd = [os.path.realpath(__main__.__file__), "exec"]
    # strings
    for arg in [
            "command", "pipeline_name", "ci_stage", "cwd", "job_id",
            "stdout_file", "stderr_file", "description", "timeout",
            "status_file", "outcome_table", "pool",
            "profile_memory_interval",
    ]:
        if arg in add_args and add_args[arg]:
            cmd.append("--%s" % arg.replace("_", "-"))
            cmd.append(shlex.quote(str(add_args[arg]).strip()))

    # lists
    for arg in [
            "inputs", "outputs", "ignore_returns", "ok_returns",
            "tags", "phony_outputs",
    ]:
        if arg not in add_args or add_args[arg] is None:
            continue
        cmd.append("--%s" % arg.replace("_", "-"))
        for item in add_args[arg]:
            cmd.append(shlex.quote(str(item).strip()))

    # switches
    for arg in [
            "timeout_ignore", "timeout_ok", "interleave_stdout_stderr",
            "profile_memory",
    ]:
        if arg in add_args and add_args[arg]:
            cmd.append("--%s" % arg.replace("_", "-"))

    return " ".join(cmd)


async def exec_job(args):
    args_dict = vars(args)
    args_dict.pop("func")
    out_data = {
        "wrapper_arguments": args_dict,
        "complete": False,
    }
    lib.util.timestamp("start_time", out_data)
    with litani.atomic_write(args.status_file) as handle:
        print(json.dumps(out_data, indent=2), file=handle)

    run = lib.process.Runner(
        args.command, args.interleave_stdout_stderr, args.cwd,
        args.timeout, args.profile_memory, args.profile_memory_interval,
        args_dict["job_id"])
    await run()
    lib.job_outcome.fill_in_result(run, out_data, args)

    for out_field, proc_pipe, arg_file in [
        ("stdout", run.get_stdout(), args.stdout_file),
        ("stderr", run.get_stderr(), args.stderr_file)
    ]:
        if proc_pipe:
            out_data[out_field] = proc_pipe.splitlines()
        else:
            out_data[out_field] = []

        if arg_file:
            out_str = proc_pipe if proc_pipe else ""
            with litani.atomic_write(arg_file) as handle:
                print(out_str, file=handle)

    if out_data["stderr"]:
        print(
            "\n".join([l.rstrip() for l in out_data["stderr"]]),
            file=sys.stderr)

    lib.util.timestamp("end_time", out_data)
    out_str = json.dumps(out_data, indent=2)
    logging.debug("run status: %s", out_str)
    with litani.atomic_write(args.status_file) as handle:
        print(out_str, file=handle)

    artifacts_dir = (litani.get_artifacts_dir() /
         out_data["wrapper_arguments"]["pipeline_name"] /
         out_data["wrapper_arguments"]["ci_stage"])
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    copier = lib.output_artifact.Copier(
        artifacts_dir, out_data["wrapper_arguments"])
    for fyle in out_data["wrapper_arguments"]["outputs"] or []:
        try:
            copier.copy_output_artifact(fyle)
        except lib.output_artifact.MissingOutput:
            logging.warning(
                "Output file '%s' of pipeline '%s' did not exist upon job "
                "completion. Not copying to artifacts directory. "
                "If this job is not supposed to emit the file, pass "
                "`--phony-outputs %s` to suppress this warning", fyle,
                out_data["wrapper_arguments"]["pipeline_name"], fyle)
        except IsADirectoryError:
            artifact_src = pathlib.Path(fyle)
            try:
                shutil.copytree(
                    fyle, str(artifacts_dir / artifact_src.name))
            except FileExistsError:
                logging.warning(
                    "Multiple files with same name in artifacts directory")

    sys.exit(out_data["wrapper_return_code"])
