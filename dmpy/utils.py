import getpass
import os
from typing import Optional


def load_query(query_name: str) -> str:
    file_name = f'{query_name}.graphql'
    parent = os.path.dirname(os.path.abspath(__file__))
    query_file_path = os.path.join(parent, 'graphql', file_name)
    if not os.path.exists(query_file_path):
        raise FileNotFoundError(f'Could not find query file {file_name}')
    with open(query_file_path, 'r') as f:
        return f.read()


def load_cookie_from_file() -> Optional[str]:
    username = getpass.getuser()
    try:
        with open(f'/tmp/{username}/cookie/sid', 'r') as f:
            return f.read().strip('\n\r')
    except:
        return None


def get_file_type(fname: str) -> str:
    base, extension = os.path.splitext(fname)
    if extension == ".gz" and base.endswith(".tar"):
        return "tar.gz"
    else:
        return extension.lstrip(".")
