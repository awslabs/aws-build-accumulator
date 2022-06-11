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


import dataclasses
import datetime
import io
import logging
import math
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time

import lib.litani



@dataclasses.dataclass
class _StatusParser:
    # Format strings documented here:
    # https://ninja-build.org/manual.html#_environment_variables
    status_format: str = "<ninja>:%r/%f/%t "
    status_re: re.Pattern = re.compile(
        r"<ninja>:(?P<running>\d+)/(?P<finished>\d+)/(?P<total>\d+) "
        r"(?P<message>.+)")


    def parse_status(self, status_str):
        m = self.status_re.match(status_str)
        if not m:
            return None
        ret = {k: int(m[k]) for k in ["running", "finished", "total"]}
        return {**ret, **{"message": m["message"]}}



@dataclasses.dataclass
class _OutputAccumulator:
    out_stream: io.RawIOBase
    status_parser: _StatusParser
    concurrency_graph: list = dataclasses.field(default_factory=list)
    finished: int = None
    total: int = None
    thread: threading.Thread = None


    @staticmethod
    def get_tty_width():
        if os.getenv("TERM") is None:
            return 80
        try:
            proc = subprocess.run(
                ["tput", "cols"], text=True, stdout=subprocess.PIPE, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        if proc.returncode:
            return None
        try:
            return int(proc.stdout.strip())
        except TypeError:
            return None


    def print_progress(self, message):
        tty_width = self.get_tty_width()
        if not tty_width:
            message_fmt = message
        else:
            f_width = int(math.log10(self.finished)) + 1 if self.finished else 1
            t_width = int(math.log10(self.total)) + 1 if self.total else 1
            progress_width = f_width + t_width + len("[/] ")

            if len(message) + progress_width <= tty_width:
                message_fmt = "[%d/%d] %s%s" % (
                    self.finished, self.total, message,
                    " " * (tty_width - len(message) - progress_width))
            else:
                message_width = tty_width - progress_width - len("...")
                message_fmt = "[%d/%d] %s..." % (
                    self.finished, self.total, message[:message_width])
        print("\r%s" % message_fmt, end="")


    def process_output(self):
        while True:
            try:
                line = self.out_stream.readline()
                if not line:
                    return
            except ValueError:
                return
            status = self.status_parser.parse_status(line)
            if not status:
                print(line)
                continue

            now = datetime.datetime.now(datetime.timezone.utc)
            now_str = now.strftime(lib.litani.TIME_FORMAT_MS)
            status["time"] = now_str
            self.concurrency_graph.append(status)

            if any((
                    status["finished"] != self.finished,
                    status["total"] != self.total)):
                self.finished = status["finished"]
                self.total = status["total"]
                self.print_progress(status["message"])


    def join(self):
        self.thread.join()
        print()


    def start(self):
        self.thread = threading.Thread(target=self.process_output)
        self.thread.start()



def _make_pgroup_leader():
    try:
        os.setpgid(0, 0)
    except OSError as err:
        logging.error(
            "Failed to create new process group for ninja (errno: %s)",
            err.errno)
        sys.exit(1)



@dataclasses.dataclass
class _SignalHandler:
    """
    Objects of this class are callable. They implement the API of a signal
    handler, and can thus be passed to Python's signal.signal call.
    """
    proc: subprocess.Popen
    render_killer: threading.Event
    pgroup: int = None


    def __post_init__(self):
        try:
            self.pgroup = os.getpgid(self.proc.pid)
        except ProcessLookupError:
            logging.error(
                "Failed to find ninja process group %d", self.proc.pid)
            sys.exit(1)


    def __call__(self, signum, _frame):
        self.render_killer.set()
        try:
            os.killpg(self.pgroup, signum)
        except OSError as err:
            logging.error(
                "Failed to send signal '%s' to ninja process group (errno: %s)",
                signum, err.errno)
            sys.exit(1)
        sys.exit(0)



@dataclasses.dataclass
class Runner:
    ninja_file: pathlib.Path
    dry_run: bool
    parallelism: int
    pipelines: list
    ci_stage: str
    render_killer: threading.Event
    proc: subprocess.CompletedProcess = None
    status_parser: _StatusParser = _StatusParser()
    out_acc: _OutputAccumulator = None
    signal_handler: _SignalHandler = None


    def _get_cmd(self):
        cmd = [
            "ninja",
            "-k", "0",
            "-f", self.ninja_file,
        ]
        if self.parallelism:
            cmd.extend(["-j", self.parallelism])
        if self.dry_run:
            cmd.append("-n")

        if self.pipelines:
            targets = ["__litani_pipeline_name_%s" % p for p in self.pipelines]
            cmd.extend(targets)
        elif self.ci_stage:
            targets = ["__litani_ci_stage_%s" % p for p in self.ci_stage]
            cmd.extend(targets)

        return [str(c) for c in cmd]


    def _register_signal_handler(self):
        sigs = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
        fails = []
        for sig in sigs:
            try:
                signal.signal(sig, self.signal_handler)
            except ValueError:
                fails.append(str(sig))
        if fails:
            logging.error(
                "Failed to set signal handler for %s", ", ".join(fails))
            sys.exit(1)


    def run(self):
        env = {
            **os.environ,
            **{"NINJA_STATUS": self.status_parser.status_format},
        }

        self.proc = subprocess.Popen(
            self._get_cmd(), env=env, stdout=subprocess.PIPE, text=True,
            preexec_fn=_make_pgroup_leader)
        self.signal_handler = _SignalHandler(self.proc, self.render_killer)
        self._register_signal_handler()

        self.out_acc = _OutputAccumulator(self.proc.stdout, self.status_parser)
        self.out_acc.start()
        self.out_acc.join()


    def was_successful(self):
        return not self.proc.returncode


    def get_parallelism_graph(self):
        trace = []
        for item in self.out_acc.concurrency_graph:
            tmp = dict(item)
            tmp.pop("message")
            trace.append(tmp)

        return {
            "trace": trace,
            "max_parallelism": max(
                [i["running"] for i in self.out_acc.concurrency_graph]),
            "n_proc": os.cpu_count(),
        }
