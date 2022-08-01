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

import argparse
import datetime
import logging
import pathlib
import sys

from lib import litani


def timestamp(format=litani.TIME_FORMAT_R):
    return datetime.datetime.now(datetime.timezone.utc).strftime(format)


def get_pools(args):
    ret = {}
    if not args.pools:
        return ret
    for pool in args.pools:
        pair = pool.split(":")
        if len(pair) != 2:
            logging.error(
                "Cannot parse pool '%s'. The correct format is a space-"
                "separated list of POOL_NAME:DEPTH", pool)
            sys.exit(1)
        name, depth = pair
        if name in ret:
            logging.error(
                "Pool name '%s' given twice (pool names must be unique)", name)
            sys.exit(1)
        try:
            ret[name] = int(depth)
        except TypeError:
            logging.error(
                "Pool depth '%s' cannot be parsed into an int", depth)
            sys.exit(1)

        if ret[name] < 1:
            logging.error(
                "Pool depth cannot be less than 1 for pool '%s'", name)
            sys.exit(1)

    return ret


def non_negative_int(arg):
    try:
        ret = int(arg)
    except ValueError as e:
        raise argparse.ArgumentTypeError(
            "Timeout '%s' must be an int" % arg) from e
    if ret < 0:
        raise argparse.ArgumentTypeError(
            "Timeout '%d' must be >= 0" % ret) from e
    return ret


def _non_directory_path(arg):
    path = pathlib.Path(arg)
    if path.exists() and path.is_dir():
        raise ValueError(
          f"--out-file flag expects a file and not a directory: {arg}")
    return path
