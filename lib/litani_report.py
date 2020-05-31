import enum
import functools
import json
import pathlib
import sys

import jinja2

from lib import litani


def get_run(cache_dir):
    with open(cache_dir / litani.CACHE_FILE) as handle:
        ret = json.load(handle)
    ret["pipelines"] = {}

    for job in ret["jobs"]:
        status_file = litani.get_status_dir() / ("%s.json" % job["job_id"])
        try:
            with open(str(status_file)) as handle:
                status = json.load(handle)
        except FileNotFoundError:
            status = {
                "complete": False,
                "wrapper-arguments": job,
            }

        pipeline_name = status["wrapper-arguments"]["pipeline_name"]
        ci_stage = status["wrapper-arguments"]["ci_stage"]

        # TODO: fill this out using a loop for goodness' sake
        try:
            ret["pipelines"][pipeline_name]["ci_stages"][ci_stage]["jobs"].append(status)
        except KeyError:
            try:
                ret["pipelines"][pipeline_name]["ci_stages"][ci_stage]["jobs"] = [status]
            except KeyError:
                try:
                    ret["pipelines"][pipeline_name]["ci_stages"][ci_stage] = {
                        "jobs": [status]
                    }
                except KeyError:
                    try:
                        ret["pipelines"][pipeline_name]["ci_stages"] = {
                            ci_stage: {
                                "name": ci_stage,
                                "jobs": [status],
                            }
                        }
                    except KeyError:
                        ret["pipelines"][pipeline_name] = {
                            "ci_stages":  {ci_stage: {"jobs": [status]}},
                            "name": pipeline_name,
                        }
    return ret


def job_sorter(j1, j2):
    if not (j1["complete"] or j2["complete"]):
        return 0
    if not j1["complete"]:
        return -1
    return j1["start-time"] < j2["start-time"]


class StageStatus(enum.IntEnum):
    FAIL = 0
    FAIL_IGNORED = 1
    SUCCESS = 2


def add_stage_stats(stage, stage_name, pipeline_name):
    n_complete_jobs = len([j for j in stage["jobs"] if j["complete"]])
    stage["progress"] = int(n_complete_jobs * 100 / len(stage["jobs"]))
    stage["complete"] = n_complete_jobs == len(stage["jobs"])
    status = StageStatus.SUCCESS
    for job in stage["jobs"]:
        try:
            if not job["complete"]:
                continue
            elif job["wrapper-return-code"]:
                status = StageStatus.FAIL
            elif job["command-return-code"] and status == StageStatus.SUCCESS:
                status = StageStatus.FAIL_IGNORED
            elif job["timeout-reached"] and status == StageStatus.SUCCESS:
                status = StageStatus.FAIL_IGNORED
        except KeyError:
            print(json.dumps(stage, indent=2))
            sys.exit(1)
    stage["status"] = status.name.lower()
    stage["url"] = "artifacts/%s/%s/index.html" % (pipeline_name, stage_name)
    stage["name"] = stage_name


class PipeStatus(enum.IntEnum):
    FAIL = 0
    IN_PROGRESS = 1
    SUCCESS = 2


def add_pipe_stats(pipe):
    pipe["url"] = "artifacts/%s/index.html" % pipe["name"]
    incomplete = [s for s in pipe["ci_stages"] if not s["complete"]]
    if incomplete:
        pipe["status"] = PipeStatus.IN_PROGRESS
    else:
        failed = [s for s in pipe["ci_stages"] if s["status"] != "success"]
        if failed:
            pipe["status"] = PipeStatus.FAIL
        else:
            pipe["status"] = PipeStatus.SUCCESS


def add_run_stats(run):
    status = PipeStatus.SUCCESS
    if [p for p in run["pipelines"] if p["status"] == PipeStatus.IN_PROGRESS]:
        status = PipeStatus.IN_PROGRESS
    if [p for p in run["pipelines"] if p["status"] == PipeStatus.FAIL]:
        status = PipeStatus.FAIL
    run["status"] = status.name.lower()
    for pipe in run["pipelines"]:
        pipe["status"] = pipe["status"].name.lower()


def sort_run(run):
    pipelines = []
    js = functools.cmp_to_key(job_sorter)
    for pipe in run["pipelines"].values():
        stages = []
        for stage in litani.CI_STAGES:
            try:
                pipeline_stage = pipe["ci_stages"][stage]
            except KeyError:
                pipe["ci_stages"][stage] = {"jobs"}
                pipeline_stage = pipe["ci_stages"][stage]
            jobs = sorted(pipeline_stage["jobs"], key=js)
            pipeline_stage["jobs"] = jobs
            add_stage_stats(pipeline_stage, stage, pipe["name"])
            stages.append(pipeline_stage)

        pipe["ci_stages"] = stages
        add_pipe_stats(pipe)
        pipelines.append(pipe)
    pipelines = sorted(pipelines, key=lambda p: p["status"])
    run["pipelines"] = pipelines
    add_run_stats(run)


def render(cache_dir):
    template_dir = pathlib.Path(__file__).parent.parent / "templates"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(template_dir)))

    report_dir = litani.get_report_dir()

    run = get_run(cache_dir)
    sort_run(run)
    templ = env.get_template("dashboard.jinja.html")
    page = templ.render(run=run)
    return page
