"""
Entry point wrapper for stressapp_raw_tool
"""

import sys

# We cannot do any fancy formatting here, since this should work
# even in ancient python versions
# Also, this must be invoked BEFORE any imports other than 'sys'
assert sys.version_info >= (3, 8), "Expecting Python 3.8 or newer"

from ideafast_platform_access.dmp_app import run_dmp_app

if __name__ == '__main__':
    args = sys.argv
    args = args[1:]
    run_dmp_app(*args)
