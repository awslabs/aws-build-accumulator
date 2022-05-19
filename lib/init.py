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

import datetime
import json
import logging
import os
import pathlib
import sys
import tempfile
import uuid

from lib import litani
import lib.util


def add_subparser(subparsers):
    init_pars = subparsers.add_parser("init")
    init_pars.set_defaults(func=init)
    for arg in [{
            "flags": ["--project-name"],
            "required": True,
            "help": "project that this proof run is associated with",
            "metavar": "NAME",
        }, {
            "flags": ["--pools"],
            "help":
                "job pools to which jobs can be added, with depth of each pool",
            "metavar": "NAME:DEPTH",
            "nargs": "+",
        }, {
            "flags": ["--output-symlink"],
            "help": "create a symbolic link from DIR to litani's output directory",
            "metavar": "DIR"
        }, {
            "flags": ["--stages"],
            "default": litani.DEFAULT_STAGES,
            "help": "stages that a job can be a member of. Default: %(default)s",
            "metavar": "NAME",
            "nargs": "+",
    }]:
        flags = arg.pop("flags")
        init_pars.add_argument(*flags, **arg)
    init_output_flags = init_pars.add_mutually_exclusive_group()
    for arg in [{
            "flags": ["--output-directory"],
            "help": "write Litani output to specified directory",
            "metavar": "DIR"
        }, {
            "flags": ["--output-prefix"],
            "help": "directory prefix to write Litani output to",
            "metavar": "DIR"
    }]:
        flags = arg.pop("flags")
        init_output_flags.add_argument(*flags, **arg)
    for arg in [{
            "flags": ["--no-print-out-dir"],
            "help": "do not print path to output directory",
            "action": "store_true"
    }]:
        flags = arg.pop("flags")
        init_pars.add_argument(*flags, **arg)


async def init(args):
    try:
        run_id = os.environ["LITANI_RUN_ID"]
    except KeyError:
        run_id = str(uuid.uuid4())

    if args.output_directory:
        cache_dir = pathlib.Path(args.output_directory).resolve()
    else:
        if args.output_prefix:
            output_prefix = pathlib.Path(args.output_prefix).resolve()
        else:
            output_prefix = pathlib.Path(tempfile.gettempdir())
        cache_dir = output_prefix / "litani" / "runs" / run_id

    try:
        cache_dir.mkdir(parents=True)
    except FileExistsError:
        logging.error("Output directory '%s' already exists", cache_dir)
        sys.exit(1)

    if args.output_symlink:
        latest_symlink = pathlib.Path(args.output_symlink).absolute()
    else:
        latest_symlink = cache_dir.parent / ("latest")
    temp_symlink = latest_symlink.with_name(
        f"{latest_symlink.name}-{str(uuid.uuid4())}")
    os.symlink(cache_dir, temp_symlink, target_is_directory=True)
    os.rename(temp_symlink, latest_symlink)

    if not args.no_print_out_dir:
        print(
            "Report will be rendered at "
            f"file://{str(latest_symlink)}/html/index.html")

    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        litani.TIME_FORMAT_W)

    with litani.atomic_write(cache_dir / litani.CACHE_FILE) as handle:
        print(json.dumps({
            "aux": {},
            "project": args.project_name,
            "version": litani.VERSION,
            "version_major": litani.VERSION_MAJOR,
            "version_minor": litani.VERSION_MINOR,
            "version_patch": litani.VERSION_PATCH,
            "release_candidate": litani.RC,
            "run_id": run_id,
            "stages": args.stages,
            "start_time": now,
            "status": "in_progress",
            "pools": lib.util.get_pools(args),
            "jobs": [],
            "parallelism": {},
            "latest_symlink": str(latest_symlink),
        }, indent=2), file=handle)

    logging.info("cache dir is at: %s", cache_dir)

    with litani.atomic_write(litani.CACHE_POINTER) as handle:
        print(str(cache_dir), file=handle)
