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
import itertools
import json
import logging
import os
import signal
import sys
import threading

from lib import litani, ninja_syntax, litani_report
import lib.exec
import lib.render
import lib.run_printer


def add_subparser(subparsers):
    run_build_pars = subparsers.add_parser("run-build")
    run_build_pars.set_defaults(func=run_build)
    for arg in [{
            "flags": ["-n", "--dry-run"],
            "help": "don't actually run jobs, just act like they succeeded",
            "action": "store_true",
    }, {
            "flags": ["-j", "--parallel"],
            "metavar": "N",
            "help": "run N jobs in parallel. 0 means infinity, default is "
                    "based on the number of cores on this system.",
    }, {
            "flags": ["-o", "--out-file"],
            "metavar": "F",
            "help": "periodically write JSON representation of the run"
    }, {
            "flags": ["--fail-on-pipeline-failure"],
            "action": "store_true",
            "help": "exit with a non-zero return code if some pipelines failed"
    }, {
            "flags": ["--no-pipeline-dep-graph"],
            "action": "store_true",
            "help": "do not attempt to generate pipeline dependency graph"
    }]:
        flags = arg.pop("flags")
        run_build_pars.add_argument(*flags, **arg)
    mutex = run_build_pars.add_mutually_exclusive_group()
    for arg in [{
            "flags": ["-p", "--pipelines"],
            "metavar": "P",
            "nargs": "+",
            "help": "only run jobs that are in the specified pipelines"
    }, {
            "flags": ["-s", "--ci-stage"],
            "metavar": "S",
            "help": (
                "only run jobs that are part of the specified ci stage. S "
            )
    }]:
        flags = arg.pop("flags")
        mutex.add_argument(*flags, **arg)


def fill_out_ninja(cache, rules, builds, pools):
    phonies = {
        "pipeline_name": {},
        "ci_stage": {},
    }

    for name, depth in cache["pools"].items():
        pools[name] = depth

    for entry in cache["jobs"]:
        outs = lib.litani.expand_args(entry["outputs"])
        ins = lib.litani.expand_args(entry["inputs"])

        if "description" in entry:
            description = entry["description"]
        else:
            description = f"Running {entry['command']}..."

        pool_name = entry.get("pool")
        if pool_name:
            if pool_name not in pools:
                logging.error(
                    "Job '%s' was added to a pool '%s' that was not "
                    "specified to `litani init`", description, pool_name)
                sys.exit(1)
            pool = {"pool": pool_name}
        else:
            pool = {}

        rule_name = entry["job_id"]
        rules.append({
            "name": rule_name,
            "description": description,
            "command": lib.exec.make_litani_exec_command(entry),
            **pool,
        })
        builds.append({
            "inputs": ins,
            "outputs": outs + [entry["status_file"]],
            "rule": rule_name,
            **pool,
        })
        if outs:
            for phony in phonies:
                try:
                    phonies[phony][entry[phony]].update(outs)
                except KeyError:
                    phonies[phony][entry[phony]] = set(outs)

    for phony, jobs in phonies.items():
        for job_name, inputs in jobs.items():
            ins = inputs or []
            builds.append({
                "inputs": sorted(list(ins)),
                "outputs": ["__litani_%s_%s" % (phony, job_name)],
                "rule": "phony",
            })


async def run_build(args):
    artifacts_dir = litani.get_artifacts_dir()
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    cache_dir = litani.get_cache_dir()
    litani.add_jobs_to_cache()

    with open(cache_dir / litani.CACHE_FILE) as handle:
        cache = json.load(handle)

    rules = []
    builds = []
    pools = {}
    fill_out_ninja(cache, rules, builds, pools)

    ninja_file = cache_dir / "litani.ninja"
    with litani.atomic_write(ninja_file) as handle:
        ninja = ninja_syntax.Writer(handle, width=70)
        for name, depth in pools.items():
            logging.debug("pool %s: %d", name, depth)
            ninja.pool(name, depth)
        for rule in rules:
            logging.debug(rule)
            ninja.rule(**rule)
        for build in builds:
            logging.debug(build)
            ninja.build(**build)
    run = litani_report.get_run_data(cache_dir)
    lib.validation.validate_run(run)
    report_dir = lib.litani.get_report_dir()
    pipeline_depgraph_renderer = litani_report.PipelineDepgraphRenderer(
        should_render=not args.no_pipeline_dep_graph)
    render = litani_report.ReportRenderer(
        report_dir, pipeline_depgraph_renderer)
    render(run)
    killer = threading.Event()
    render_thread = threading.Thread(
        group=None, target=lib.render.continuous_render_report,
        args=(cache_dir, killer, args.out_file, render))
    render_thread.start()

    runner = lib.ninja.Runner(
        ninja_file, args.dry_run, args.parallel, args.pipelines,
        args.ci_stage)

    lib.pid_file.write()
    sig_handler = lib.run_printer.DumpRunSignalHandler(cache_dir)
    signal.signal(lib.run_printer.DUMP_SIGNAL, sig_handler)
    runner.run()

    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        litani.TIME_FORMAT_W)

    with open(cache_dir / litani.CACHE_FILE) as handle:
        run_info = json.load(handle)
    run_info["end_time"] = now
    run_info["parallelism"] = runner.get_parallelism_graph()

    success = True
    for root, _, files in os.walk(litani.get_status_dir()):
        for fyle in files:
            if not fyle.endswith(".json"):
                continue
            with open(os.path.join(root, fyle)) as handle:
                job_status = json.load(handle)
            if job_status["outcome"] != "success":
                success = False
    run_info["status"] = "success" if success else "failure"

    with litani.atomic_write(cache_dir / litani.CACHE_FILE) as handle:
        print(json.dumps(run_info, indent=2), file=handle)

    killer.set()
    render_thread.join()
    run = litani_report.get_run_data(cache_dir)
    lib.validation.validate_run(run)
    render(run)

    with litani.atomic_write(cache_dir / litani.RUN_FILE) as handle:
        print(json.dumps(run, indent=2), file=handle)
    if args.out_file:
        with litani.atomic_write(args.out_file) as handle:
            print(json.dumps(run, indent=2), file=handle)

    report_rendering = litani.ReportRendering()
    report_rendering.complete()

    # Print the path to the complete report at the end of 'litani run-build'.
    # The same path was printed at the start of 'litani init'.
    if 'latest_symlink' in run_info:
        print("Report was rendered at "
              f"file://{run_info['latest_symlink']}/html/index.html")

    if args.fail_on_pipeline_failure:
        for _ in itertools.filterfalse(
                lambda pipe: pipe["status"] != "fail", run["pipelines"]):
            sys.exit(10)
        sys.exit(0)

    sys.exit(0)
