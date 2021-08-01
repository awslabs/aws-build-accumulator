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
import pathlib
import shutil



class MissingOutput(Exception):
    pass



@dataclasses.dataclass
class Copier:
    """Copy output artifacts to a directory, raising if they don't exist"""

    artifacts_dir: pathlib.Path
    job_args: dict


    def copy_output_file(self, fyle):
        try:
            shutil.copy(fyle, self.artifacts_dir)
        except FileNotFoundError as e:
            if "phony_outputs" not in self.job_args:
                raise MissingOutput() from e

            if self.job_args["phony_outputs"] is None:
                raise MissingOutput() from e

            if not self.job_args["phony_outputs"]:
                # User supplied an empty list of phony outputs, so all outputs
                # are considered phony
                return

            if fyle in self.job_args["phony_outputs"]:
                return

            raise MissingOutput() from e
