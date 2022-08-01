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

import json
import logging
import time
import traceback


from lib import aws_s3, litani, litani_report
import lib.validation


def continuous_render_report(cache_dir, killer, out_file, render, bucket_name):
    try:
        while True:
            run = litani_report.get_run_data(cache_dir)
            lib.validation.validate_run(run)
            with litani.atomic_write(cache_dir / litani.RUN_FILE) as handle:
                print(json.dumps(run, indent=2), file=handle)
            if out_file is not None:
                with litani.atomic_write(out_file) as handle:
                    print(json.dumps(run, indent=2), file=handle)
            render(run)
            if killer.is_set():
                break
            if bucket_name:
                aws_s3.sync(bucket_name, cache_dir, litani.INCREMENTAL)
            time.sleep(2)
    except BaseException as e:
        logging.error("Continuous render function crashed")
        logging.error(str(e))
        traceback.print_exc()
