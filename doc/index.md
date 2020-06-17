<header id="title">
  <h1>AWS Litani</h1>
  <p id="subtitle">Build Abstraction Layer</p>
</header><!-- id="title" -->

Litani collects build jobs from multiple sources before executing them
concurrently.

Litani allows you to use multiple build systems in the same project,
providing a backend that each build system emits jobs to.
Once all jobs have been enqueued, Litani executes them all as a single
unified build graph.
Litani also provides platform-independent job control (timeouts and
control of return codes), as well as grouping of job artifacts into
stages.

[Source code repository](https://github.com/awslabs/litani)


Overview
--------

Consider the following Makefile:

    foo.out: foo.in
        timeout 90 my_command $^ > $@; if [ $? -eq 10 ]; then exit 0; fi

`foo.out` is built from `foo.in` using `my_command`. We want to kill
`my_command` if it runs for more than 90 seconds, and we're also
expecting that `my_command` may exit with a return code of 10; we don't
consider that to be an error, so we exit the subshell with 0 in that
case.

The timeout and error escaping in this command are unportable. We can
replace it with an invocation to Litani as follows:

    foo.out: foo.in
        litani add-job                \
          --command "my_command $^"   \
          --inputs $^                 \
          --outputs $@                \
          --timeout 90                \
          --ok-returns 10             \
          --pipeline-name my_command  \
          --ci-stage build            \
          --stdout-file $@

To actually run this, write the following shell script:

    #!/bin/sh

    litani init --project my_project
    make foo.out
    litani exec

Running `make` doesn't actually run the job; rather, it runs Litani,
which saves the job for later. You can run `litani add-job` as many
times as you like after running `litani init`; all these jobs are cached
and turned into a dependency graph using the arguments to `--inputs` and
`--outputs`. Running `litani exec` runs all cached build jobs together,
in parallel if possible.

Litani continuously updates a `run.json` file while the `exec` command
is running, showing progress of each job as well as recording the return
codes, timeout information, and stdout/stderr of each job. This file is
documented below and is designed to be easy to render into a dashboard,
for example in HTML.


Motivation
----------

While the platform-independent job-control features are a nice bonus,
Litani's real value is in serving as a backend for executing a graph of
build tasks that are added from heterogeneous sources. In a complex
software project, different parts of the project can use incompatible
build systems. To build the entire project, one must either run all
build systems in parallel&mdash;potentially overcommitting on
concurrency and introducing nondeterminism when some of the targets
overlap&mdash;or run each build system serially, wasting time.

Litani makes it possible for jobs that are specified in different build
systems to depend on each other. It also obviates the need to force
different parts of the project to use a unified build syntax, if that is
unnatural for some reason. If some parts of the build tree are specified
in Make, with others specified in CMake, then Litani allows developers
working on each part of the codebase to use the build system that makes
sense to them, while Litani builds the entire tree in the background.


Subtool Reference
-----------------

Litani consists of three user-facing commands:

* `litani init`&mdash;create a new cache to add jobs to
* `litani add-job`&mdash;add a job to the cache for future execution
* `litani exec`&mdash;run all jobs in the cache in dependency order


### `litani init`
### `litani add-job`
### `litani run-build`


Data Format Reference
---------------------

Litani emits two sets of files:

* `jobs/*.json`, each containing the details of a job to be executed
* `run.json`, containing the details of an in-progress or completed execution


### `job/*.json` file
### `run.json` file
