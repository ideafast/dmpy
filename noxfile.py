import tempfile
from typing import Any

import nox
from nox.sessions import Session

nox.options.sessions = "lint", "tests"
locations = "dmpy", "noxfile.py", "tests/test_client.py"


def install_with_constraints(session: Session, *args: str, **kwargs: Any) -> None:
    """A wrapper for session.install use linting and
    test depenencies that are pinned. This ensure
    replicatability amongst developers."""
    with tempfile.NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--dev",
            "--format=requirements.txt",
            "--without-hashes",
            f"--output={requirements.name}",
            external=True,
        )
        session.install(f"--constraint={requirements.name}", *args, **kwargs)


@nox.session(python=["3.8"])
def black(session: Session) -> None:
    """Automatic format code following black codestyle:
    https://github.com/psf/black
    """
    args = session.posargs or locations
    install_with_constraints(session, "black")
    session.run("black", *args)


@nox.session(python=["3.8"])
def lint(session: Session) -> None:
    """Provide lint warnings to help enforce style guide."""
    args = session.posargs or locations
    install_with_constraints(
        session,
        "flake8",
        "flake8-aaa",
        "flake8-bandit",
        "flake8-black",
        "flake8-bugbear",
    )
    session.run("flake8", *args)


@nox.session(python=["3.8"])
def tests(session: Session) -> None:
    """Setup for automated testing with pytest"""
    args = session.posargs
    session.run("poetry", "install", "--no-dev", external=True)
    install_with_constraints(session, "pytest")
    session.run("pytest", *args)
