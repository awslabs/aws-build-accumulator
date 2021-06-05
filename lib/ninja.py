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


import asyncio
import dataclasses
import pathlib
import subprocess



@dataclasses.dataclass
class Runner:
    ninja_file: pathlib.Path
    dry_run: bool
    parallelism: int
    pipelines: list
    ci_stage: str
    proc: subprocess.CompletedProcess = None


    def _get_args(self):
        args = [
            "-k", "0",
            "-f", self.ninja_file,
        ]
        if self.parallelism:
            args.extend(["-j", self.parallelism])
        if self.dry_run:
            args.append("-n")

        if self.pipelines:
            targets = ["__litani_pipeline_name_%s" % p for p in self.pipelines]
            args.extend(targets)
        elif self.ci_stage:
            targets = ["__litani_ci_stage_%s" % p for p in self.ci_stage]
            args.extend(targets)

        return [str(c) for c in args]


    async def run(self):
        args = self._get_args()
        self.proc = await asyncio.create_subprocess_exec("ninja", *args)
        await self.proc.wait()


    def was_successful(self):
        return not self.proc.returncode
