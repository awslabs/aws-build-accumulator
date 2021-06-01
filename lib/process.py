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


import abc
import asyncio
import dataclasses
import datetime
import decimal
import logging
import platform
import subprocess
import sys

import lib.litani



@dataclasses.dataclass
class _Process:
    command: str
    interleave_stdout_stderr: bool
    timeout: int
    cwd: str
    proc: subprocess.CompletedProcess = None
    stdout: str = None
    stderr: str = None
    timeout_reached: bool = None


    async def __call__(self):
        if self.interleave_stdout_stderr:
            pipe = asyncio.subprocess.STDOUT
        else:
            pipe = asyncio.subprocess.PIPE

        proc = await asyncio.create_subprocess_shell(
            self.command, stdout=asyncio.subprocess.PIPE, stderr=pipe,
            cwd=self.cwd)
        self.proc = proc

        timeout_reached = False
        try:
            out, err = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout)
        except asyncio.TimeoutError:
            proc.terminate()
            await asyncio.sleep(1)
            proc.kill()
            out, err = await proc.communicate()
            timeout_reached = True

        self.stdout = out
        self.stderr = err
        self.timeout_reached = timeout_reached



class Runner:
    def __init__(
            self, command, interleave_stdout_stderr, cwd, timeout):
        self.tasks = []
        self.runner = _Process(
            command=command, interleave_stdout_stderr=interleave_stdout_stderr,
            cwd=cwd, timeout=timeout)
        self.tasks.append(self.runner)


    async def __call__(self):
        tasks = []
        for task in self.tasks:
            tasks.append(asyncio.create_task(task()))
        _, pending = await asyncio.wait(
            tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()
            await task


    def get_proc(self):
        return self.runner.proc


    def get_stdout(self):
        if self.runner.stdout:
            return self.runner.stdout.decode("utf-8")
        return None


    def get_stderr(self):
        if self.runner.stderr:
            return self.runner.stderr.decode("utf-8")
        return None


    def reached_timeout(self):
        return self.runner.timeout_reached


