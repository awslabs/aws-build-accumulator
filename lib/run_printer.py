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


"""Signal the run-build process to dump its run file and print it"""


import dataclasses
import json
import os
import pathlib
import random
import signal
import sys
import time

import lib.litani
import lib.litani_report
import lib.pid_file


"""When run-build receives this Unix signal, it will write the run file"""
DUMP_SIGNAL = signal.SIGUSR1
_DUMPED_RUN = "dumped-run.json"



@dataclasses.dataclass
class BackoffSleeper:
    jitter: float
    duration: float = 0.2
    multiplier: int = 2


    def sleep(self):
        time.sleep(self.duration)

        self.duration += self.jitter
        self.duration *= self.multiplier
        self.jitter *= self.multiplier



def _exit_success(run):
    print(json.dumps(run, indent=2))
    sys.exit(0)


def _exit_error():
    print(json.dumps(None))
    sys.exit(0)


def _try_dump_run(cache_dir, pid, sleeper):
    os.kill(pid, DUMP_SIGNAL)
    try:
        with open(cache_dir / _DUMPED_RUN) as handle:
            run = json.load(handle)
        _exit_success(run)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        sleeper.sleep()


async def dump_run(args):
    random.seed()

    try:
        pid = lib.pid_file.read()
    except FileNotFoundError:
        _exit_error()

    cache_dir = lib.litani.get_cache_dir()

    sleeper = BackoffSleeper(jitter=random.random())
    if args.retries:
        for _ in range(args.retries):
            _try_dump_run(cache_dir, pid, sleeper)
    else:
        while True:
            _try_dump_run(cache_dir, pid, sleeper)
    _exit_error()



@dataclasses.dataclass
class DumpRunSignalHandler:
    """Signal handler matching the API of the argument to signal.signal()"""

    cache_dir: pathlib.Path


    def __call__(self, _signum, _frame):
        run = lib.litani_report.get_run_data(self.cache_dir)
        with lib.litani.atomic_write(
                self.cache_dir / _DUMPED_RUN) as handle:
            print(json.dumps(run, indent=2), file=handle)
