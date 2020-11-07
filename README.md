# IDEA-FAST Data Management Portal (DMP) Python CLI & Library

Python package to access the IDEA FAST Data Management Portal (DMP) via the command line (CLI)
and through a core library that exposes a subset of methods for authentication, viewing, and data upload.

## Using Command Line Interface (CLI)

You can run the CLI programme to login, view, download, and upload data to the DMP 
all from within your terminal. The expanded documentation is [here](CLI.md) otherwise run:

    poetry run cli

## Local Development

[Poetry](https://python-poetry.org/) is used for dependency management and
[pyenv](https://github.com/pyenv/pyenv) to manage python installations, so
please install both on your local machine. Python 3.8 is used by default and can
be installed as follows:

```sh
$ pyenv install 3.8.0 && pyenv global 3.8.0
```

Then install all dependencies for this project through poetry by running:

```sh
$ poetry install
```

To use the virtual environment poetry created:

```sh
$ poetry shell
```

[Nox](https://nox.thea.codes/) is installed as a development dependency and is used used to simplfy running tests, code formatting, and linting. To run all nox commands (black, lint, tests):

```sh
$ poetry run nox -r
```

```sh
$ poetry run nox -rs black
```