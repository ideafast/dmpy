import sys

from ideafast_dmp.dmp_app import run_dmp_app


def main():
    args = sys.argv
    args = args[1:]
    run_dmp_app(*args)
