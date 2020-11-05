# IDEA-FAST Data Management Portal Python Library

 Python package to access the Data Management Portal 

## Local Development

[Poetry](https://python-poetry.org/) is used for dependency management and
[pyenv](https://github.com/pyenv/pyenv) to manage python installations, so
please install both on your local machine. We use python 3.8 by default, so
please make sure this is installed via pyenv, e.g.

    pyenv install 3.8.0 && pyenv global 3.8.0

Once done, you can install dependencies for this project via:

    poetry install

To setup a virtual environment with your local pyenv version run:

    poetry shell