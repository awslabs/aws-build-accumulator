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

import logging
import os
import subprocess

from lib import litani, util


def _run_aws_s3_sync_command(command, **kwds):
    if "shell" in kwds and kwds["shell"]:
        cmd_str = command
    else:
        cmd_str = " ".join([str(c) for c in command])
    logging.info("Command: %s", cmd_str)
    # pylint: disable=subprocess-run-check
    proc = subprocess.run(command, **kwds)
    if proc.returncode:
        logging.error("Failed to run '%s'", cmd_str)
    return proc


def _to_local_path(*components):
    return f"{os.path.join(*components)}/"


def _to_s3_uri(bucket_name, location):
    return f"s3://{bucket_name}/{location}"


def sync(bucket_name, cache_dir, report_dir_type):
    html_dir = cache_dir / "html"
    util.zip_directory(html_dir, report_dir_type)

    local_path = _to_local_path(html_dir)
    run_id = litani.get_run_id()
    location = f"{litani.BUILD_ARTIFACTS}/{run_id}/{report_dir_type}"
    if report_dir_type == litani.INCREMENTAL:
        snapshot = util.timestamp(format=litani.TIME_FORMAT_FILENAME_FRIENDLY)
        location = f"{location}/{snapshot}"
        exclude = str(html_dir / "artifacts" / "*")
    s3_uri = _to_s3_uri(bucket_name, location)
    sync_cmd = ["aws", "s3", "sync", local_path, s3_uri, "--only-show-errors"]
    if report_dir_type == litani.INCREMENTAL:
        sync_cmd.extend(["--exclude", exclude])
    attempts = 1 if report_dir_type == litani.INCREMENTAL else 5

    for i in range(attempts):
        logging.info(
            "Copying %s to %s - Attempt #%s", local_path, location, str(i+1))
        proc = _run_aws_s3_sync_command(sync_cmd)
        if proc.returncode == 0:
            return
