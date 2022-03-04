Litani
=

Litani is a build system that provides an HTML dashboard of job results, as well
as a JSON-formatted record of job results. It provides platform-independent job
control (timeouts, return code control) and an output format that is easy to
render into reports (for example, using the built-in renderer).

### Documentation

Hosted [here](https://awslabs.github.io/aws-build-accumulator/). The Homebrew
and Debian packages also install the man pages locally, try
`man litani-add-job`.


### Installation

To install with [Homebrew](https://brew.sh):

```bash
brew tap aws/tap
brew install litani
```

### Dependencies

If you are cloning the source code, you will need the following dependencies:

#### Required

* Python3
* [Ninja](https://ninja-build.org/)
  * `apt-get install ninja-build`, `brew install ninja`
* [Jinja](https://jinja.palletsprojects.com/en/2.11.x/)
  * `pip3 install jinja2`

#### Recommended

* [Graphviz DOT](https://graphviz.org/)
  * `apt-get install graphviz`, `brew install graphviz`
* [Gnuplot](http://www.gnuplot.info/) to generate graphs on the dashboard
  * `apt-get install gnuplot`, `brew install gnuplot`

#### Optional

* [Voluptuous](https://pypi.org/project/voluptuous/) to perform
  sanity-checking on internal data structures
  * `pip3 install voluptuous`
* [scdoc](https://git.sr.ht/~sircmpwn/scdoc) to build the documentation
  * `brew install scdoc`
