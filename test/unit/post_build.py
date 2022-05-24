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


import json
import pathlib
import unittest
import unittest.mock

import lib.post_build


class TestSummarizeResults(unittest.TestCase):
    def setUp(self):
        self.run_file = pathlib.Path().cwd() / "test/unit/sample_run.json"


    def test_get_summary(self):
        expected = json.dumps({
            "Breakdown of statuses across pipelines": {
                "Fail": 1,
                "Success": 1
            },
            "Breakdown of status per pipeline": {
                "pipe-will-fail": "Fail",
                "pipe-will-succeed": "Success"
            }
        }, indent=2)
        with open(self.run_file) as fp:
            contents = json.load(fp)
            actual = lib.post_build.get_summary(contents)
            self.assertEqual(expected, actual)
