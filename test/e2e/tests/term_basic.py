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


import logging
import os
import pathlib
import signal
import sys
import time


def get_init_args():
    return {
        "kwargs": {
            "project": "foo",
        }
    }


def get_jobs():
    ret = []
    test_dir = pathlib.Path(__file__).parent.parent.parent
    for _ in range(30):
        ret.append({
        "kwargs": {
            "command": test_dir / "bin/write-pid-and-sleep",
            "ci-stage": "build",
            "pipeline": "foo",
        }
    })
    return ret


def get_run_build_args():
    return {}


def on_run():
    time.sleep(5)
    with open(".litani_cache_dir") as handle:
        cache_dir = pathlib.Path(handle.read().strip())
    with open(cache_dir / "run-pid") as handle:
        pid = int(handle.read().strip())
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        logging.error("Unable to terminate litani run-build")
        sys.exit(1)
    time.sleep(5)

    cnt = 0
    for pid_file in pathlib.Path("pids").iterdir():
        try:
            os.kill(int(pid_file.stem), 0)
        except OSError as exc:
            pass
        else:
            cnt += 1

    if cnt:
        logging.error(
            "%d write-pid-and-sleep processes existed after termination", cnt)
        sys.exit(1)


def check_run(run):
    return True
