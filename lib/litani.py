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
import contextlib
import dataclasses
import json
import logging
import os
import pathlib
import signal
import shutil
import subprocess
import sys
import uuid


CACHE_FILE = "cache.json"
CACHE_POINTER = ".litani_cache_dir"
DEFAULT_STAGES = ["build", "test", "report"]
ENV_VAR_JOB_ID = "LITANI_JOB_ID"
JOBS_DIR = "jobs"
RUN_FILE = "run.json"
TIME_FORMAT_R = "%Y-%m-%dT%H:%M:%SZ"
TIME_FORMAT_W = "%Y-%m-%dT%H:%M:%SZ"
TIME_FORMAT_MS = "%Y-%m-%dT%H:%M:%S.%fZ"
VERSION_MAJOR = 1
VERSION_MINOR = 26
VERSION_PATCH = 0
RC = True

RC_STR = "-rc" if RC else ""
VERSION = "%d.%d.%d%s" % (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, RC_STR)



@dataclasses.dataclass
class DescendentTerminator:
    """
    Objects of this class are callable. They implement the API of a signal
    handler, and can thus be passed to Python's signal.signal call.
    """
    proc: subprocess.Popen
    pgroup: int = None


    def __post_init__(self):
        try:
            self.pgroup = os.getpgid(self.proc.pid)
        except ProcessLookupError:
            logging.error(
                "Failed to find process group %d", self.proc.pid)
            sys.exit(1)


    def __call__(self, signum, _frame):
        try:
            os.killpg(self.pgroup, signum)
        except OSError as err:
            logging.error(
                "Failed to send signal '%s' to process group (errno: %s)",
                signum, err.errno)
            sys.exit(1)
        sys.exit(0)



class ExpireableDirectory:
    """This class is to mark directories as being safe for garbage collection"""

    def __init__(self, path: pathlib.Path):
        self._touchfile = path.resolve() / ".litani-expired"


    def expire(self):
        self._touchfile.touch()


    def is_expired(self):
        return self._touchfile.exists()



class AcquisitionFailed(Exception):
    pass



class TimeoutExpired(Exception):
    pass


class CacheDir:
    cache_dir_path: pathlib.Path = None

    @staticmethod
    def get(lookup_path=os.getcwd()):
        if CacheDir.cache_dir_path:
            return CacheDir.cache_dir_path

        for possible_dir in CacheDir.cache_pointer_dirs(lookup_path):
            logging.debug(
                "Searching for cache pointer in %s", possible_dir)
            possible_pointer = possible_dir / CACHE_POINTER
            try:
                if possible_pointer.exists():
                    logging.debug(
                        "Found a cache pointer at %s", possible_pointer)
                    with open(possible_pointer) as handle:
                        pointer = handle.read().strip()
                    possible_cache = pathlib.Path(pointer)
                    if not possible_cache.exists():
                        logging.warning(
                            "Found a cache file at %s pointing to %s, but that "
                            "directory does not exist. Continuing search...",
                            possible_pointer, possible_cache)
                        continue
                    logging.debug("cache is at %s", possible_cache)
                    CacheDir.cache_dir_path = possible_cache
                    return possible_cache

            except PermissionError:
                pass

        logging.error(
            "Could not find a pointer to a litani cache. Did you forget "
            "to run `litani init`?")
        raise FileNotFoundError

    @staticmethod
    def cache_pointer_dirs(lookup_path):
        current = pathlib.Path(lookup_path).resolve(strict=True)
        yield current
        while current.parent != current:
            current = current.parent
            yield current


class LockableDirectory:
    """POSIX-compliant directory locking"""


    def __init__(self, path: pathlib.Path):
        """Directory is initially locked"""

        self.path = path.resolve()
        self._lock_file = self.path / ".litani-lock"


    # Non-blocking =============================================================


    def acquire(self):
        """Return True if acquisition was successful, False otherwise"""
        try:
            self._lock_file.unlink()
        except OSError:
            return False
        else:
            return True


    def release(self):
        self._lock_file.touch()


    @contextlib.contextmanager
    def try_acquire(self):
        """Automatically releases directory at the end of a block. Usage:

                try:
                    with lock_dir.try_acquire():
                        # do stuff with locked dir
                except report_directories.AcquisitionFailed:
                    # deal with it
        """

        if not self.acquire():
            raise AcquisitionFailed("directory: '%s'" % self.path)
        yield
        self.release()


    # Async ====================================================================


    async def acquire_wait(self, timeout=0):
        """Block until acquisition succeeds or timeout expires"""

        while True:
            if self.acquire():
                return
            timeout -= 1
            if timeout == 0:
                raise TimeoutExpired(
                    "directory: '%s', timeout: %d" % (self.path, timeout))
            await asyncio.sleep(1)


    @contextlib.contextmanager
    async def try_acquire_wait(self, timeout=0):
        """Enter a context manager as soon as acquisition succeeds. Directory
        will be released upon exit from context manager. Usage:

                try:
                    with await lock_dir.try_acquire_wait(timeout=10):
                        # do stuff with locked dir
                except report_directories.TimeoutExpired:
                    # deal with it
        """

        with await self.acquire_wait(timeout):
            yield
        self.release()



def register_signal_handler(handler):
    sigs = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)
    fails = []
    for sig in sigs:
        try:
            signal.signal(sig, handler)
        except ValueError:
            fails.append(str(sig))
    if fails:
        logging.error(
            "Failed to set signal handler for %s", ", ".join(fails))
        sys.exit(1)


def make_pgroup_leader():
    try:
        os.setpgid(0, 0)
    except OSError as err:
        logging.error(
            "Failed to create new process group (errno: %s)",
            err.errno)
        sys.exit(1)


def get_cache_dir(path=os.getcwd()):
    try:
        return CacheDir.get(path)
    except FileNotFoundError:
        sys.exit(1)


def get_report_dir():
    return get_cache_dir() / "html"


def get_report_data_dir():
    return get_cache_dir() / "report_data"


def get_artifacts_dir():
    return get_cache_dir() / "artifacts"


def get_status_dir():
    return get_cache_dir() / "status"


@contextlib.contextmanager
def atomic_write(path, mode="w"):
    try:
        parent = pathlib.Path(path).parent
        parent.mkdir(exist_ok=True, parents=True)
        tmp = "%s~%s" % (path, str(uuid.uuid4()))
        # pylint: disable=consider-using-with
        handle = open(tmp, mode)
        yield handle
    except RuntimeError:
        try:
            os.unlink(tmp)
        except RuntimeError:
            pass
    else:
        handle.flush()
        handle.close()
        try:
            os.rename(tmp, path)
        except RuntimeError:
            os.unlink(tmp)


def add_jobs_to_cache():
    """Adds individual Litani jobs in the jobs directory to the cache file

    `litani add-job` adds jobs to individual JSON files so that it's possible to
    run multiple parallel invocations of `litani add-job`. When all jobs have
    been added, this method should be called so that all of the individual JSON
    job files get added to the single cache file, ready to be run.
    """
    jobs = []
    cache_dir = get_cache_dir()
    jobs_dir = cache_dir / JOBS_DIR
    if not jobs_dir.exists():
        logging.error(
            "Cannot run build: no jobs were added. Run `litani add-job` one or "
            "more times before running `litani run-build`.")
        sys.exit(1)
    for job_file in os.listdir(jobs_dir):
        with open(jobs_dir / job_file) as handle:
            jobs.append(json.load(handle))

    with open(cache_dir / CACHE_FILE) as handle:
        cache = json.load(handle)
    cache["jobs"] = jobs
    with atomic_write(cache_dir / CACHE_FILE) as handle:
        print(json.dumps(cache, indent=2), file=handle)


def unlink_expired():
    """Delete all report directories that are expired and unlocked"""

    for data_dir in get_report_data_dir().iterdir():
        lock_dir = LockableDirectory(data_dir)
        if not lock_dir.acquire():
            continue
        expire_dir = ExpireableDirectory(data_dir)
        if expire_dir.is_expired():
            logging.debug("Unlinking %s", str(data_dir))
            shutil.rmtree(data_dir)
            # No need to release lock after deletion
        else:
            lock_dir.release()


def expand_args(files):
    """Produce a list of files by expanding any "@"-prefixed file names to their
    JSON-list contents.
    """
    if not files:
        return []

    result = []
    for f in files:
        if f.startswith("@"):
            with open(f[1:]) as json_file:
                result.extend(json.load(json_file))
        else:
            result.append(f)

    return result
