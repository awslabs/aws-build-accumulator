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
import json
import os
import pathlib
import sys

import lib.litani
import lib.jobs


@dataclasses.dataclass
class _JobsTransformer:
    jobs_dir: pathlib.Path
    old_uuids: list


    async def __call__(self, user_jobs):
        self._delete_old_jobs()
        await self._add_new_jobs(user_jobs)


    async def _add_new_jobs(self, user_jobs):
        for job in user_jobs:
            job["subcommand"] = "add-job"
            await lib.jobs.add_job(job)


    def _delete_old_jobs(self):
        for uuid in self.old_uuids:
            job_file = self.jobs_dir / ("%s.json" % uuid)
            try:
                os.unlink(job_file)
            except FileNotFoundError:
                continue



def _read_jobs():
    in_text = sys.stdin.read()
    return json.loads(in_text)


async def main(_):
    jobs_dir = lib.litani.get_cache_dir() / lib.litani.JOBS_DIR
    old_uuids = set()
    for job in jobs_dir.iterdir():
        old_uuids.add(str(job.stem))

    lib.jobs.print_jobs()

    new_jobs = _read_jobs()

    transform = _JobsTransformer(jobs_dir, old_uuids)
    await transform(new_jobs)
