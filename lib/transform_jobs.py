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
import logging
import os
import pathlib
import sys

import lib.litani


@dataclasses.dataclass
class _JobsTransformer:
    jobs_dir: pathlib.Path
    old_uuids: list


    def __call__(self, user_jobs):
        for uuid in self.old_uuids:
            job_file = self.jobs_dir / ("%s.json" % uuid)
            try:
                with open(job_file) as handle:
                    old_job = json.load(handle)
                    uuid = old_job["job_id"]
            except FileNotFoundError:
                logging.warning(
                    "file for job %s disappeared; not updating", uuid)
                continue

            updated_job = [
                j for j in user_jobs if j["job_id"] == uuid
            ]
            if not updated_job:
                self._delete_job(old_job)
            elif len(updated_job) > 1:
                logging.error(
                    "user input contained two jobs with uuid %s", uuid)
                sys.exit(1)
            elif updated_job[0] == old_job:
                self._write_unmodified_job(old_job)
            else:
                self._write_transformed_job(updated_job[0])

        new_jobs = [
            j for j in user_jobs
            if j["job_id"] not in self.old_uuids]
        for job in new_jobs:
            self._write_new_job(job)


    @staticmethod
    def _job_name(job):
        desc = f" ({job['description']})" if job["description"] else ''
        return f"{job['job_id']}{desc}"


    def _path_to_job(self, job):
        return self.jobs_dir / ("%s.json" % job["job_id"])


    def _write_new_job(self, job):
        logging.info("writing new job %s", self._job_name(job))
        with lib.litani.atomic_write(self._path_to_job(job)) as handle:
            print(json.dumps(job, indent=2), file=handle)


    def _write_unmodified_job(self, job):
        logging.debug("not changing job %s", self._job_name(job))


    def _write_transformed_job(self, job):
        logging.info("transforming job %s", self._job_name(job))
        with lib.litani.atomic_write(self._path_to_job(job)) as handle:
            print(json.dumps(job, indent=2), file=handle)


    def _delete_job(self, job):
        logging.info("deleting job %s", self._job_name(job))
        os.unlink(self._path_to_job(job))



def _print_jobs(job_paths):
    out = []
    for job in job_paths:
        with open(job) as handle:
            out.append(json.load(handle))
    print(json.dumps(out, indent=2))
    sys.stdout.flush()
    os.close(sys.stdout.fileno())


def _read_jobs():
    in_text = sys.stdin.read()
    return json.loads(in_text)


async def main(_):
    jobs_dir = lib.litani.get_cache_dir() / lib.litani.JOBS_DIR
    old_jobs = list()
    old_uuids = set()
    for job in jobs_dir.iterdir():
        old_jobs.append(job)
        old_uuids.add(str(job.stem))

    _print_jobs(old_jobs)

    new_jobs = _read_jobs()

    transform = _JobsTransformer(jobs_dir, old_uuids)
    transform(new_jobs)
