# DMPy: IDEA-FAST Data Management Portal Python CLI and Client

Python package to access the IDEA FAST Data Management Portal (DMP) via the command line (CLI)
and through a library that exposes a subset of methods for authentication, viewing data, and upload.

## Using Command Line Interface (CLI)

The CLI programme can be used to login, view, download, and upload data to the DMP. 
The assocaited CLI documentation such as parameters is documented [here](CLI.md).

## Local Development

We recommend installing [pyenv](https://github.com/pyenv/pyenv) to manage python installations, 
and [poetry](https://python-poetry.org/) is used for dependency management. 
Python 3.8 is used by default and can be installed and set as follows:

```sh
$ pyenv install 3.8.0 && pyenv global 3.8.0
```

Dependencies are split into three parts: `cli`, `client`, and `dev` as outlined in [./pyproject.toml](./pyproject.toml).

```sh
# Installs all including devs but not "extras"
$ poetry install
# If you plan to run the CLI locally
$ poetry install -E cli
```

To use the virtual environment poetry created:

```sh
$ poetry shell
```

### Setting up .env

Rename `.dmpy.env.example` to `.dmpy.env` and add relevant local/live values and credentials. 

**Note:** `\n` in DMP_PUBLIC_KEY will need to be escaped, e.g., `\n` converted to `\\n` 

### Testing, Linting, & Code Formatting

[Nox](https://nox.thea.codes/) is installed as a development dependency through poetry and is used used to simplfy running tests, code formatting, and linting. To run _all_ nox commands ([black](https://github.com/psf/black), [lint](https://flake8.pycqa.org/en/latest/), [tests](https://docs.pytest.org/en/latest/)):

```sh
$ poetry run nox -r
```

To run a specific command, e.g. automatic code formatting:

```sh
$ poetry run nox -rs black
```