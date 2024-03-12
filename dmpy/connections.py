from typing import Dict
from dmpy.utils import load_query, load_cookie_from_file, load_host_from_file
import requests
import os
import json


class DMPConnection:
    def __init__(self):
        if os.environ.get('DMP_URL'):
            host = os.environ.get('DMP_URL')
        else:
            host = load_host_from_file()
            if host is None:
                host = 'https://data.ideafast.eu'
            else:
                host = f'https://{host}'

        if os.environ.get('DMP_COOKIE'):
            cookie = os.environ.get('DMP_COOKIE')
        else:
            cookie = load_cookie_from_file()
        self._host = host
        self._host_graphql = f'{host}/graphql'
        self._cookies = {"connect.sid": cookie}

    def graphql_request(self, name: str, variables: any):
        headers = {
            "Content-Type": "application/json",
        }
        query = load_query(name)
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
        response = requests.post(self._host_graphql, json={'query': query, 'variables': variables}, headers=headers,
                                 cookies=self._cookies)
        if response.status_code != 200:
            raise Exception(f'Failed to query {name}: {response.text}')
        return response.json()

    def get_file(self, file_id: str, stream=True):
        url = f'{self._host}/file/{file_id}'
        response = requests.get(url, cookies=self._cookies, stream=stream)
        if response.status_code != 200:
            raise Exception(f'Failed to download file {file_id}: {response.text}')
        return response.content

    def upload_file(self, file_name: str, file_content: bytes, variables: any):
        query = load_query("upload")
        
        operations: Dict[str, Dict] = {
            'query': query,
            'variables': variables,
        }

        map_value: Dict[str, list] = {
            'x': ['variables.file'],
        }

        data: Dict[str, str] = {
            'operations': json.dumps(operations),
            'map': json.dumps(map_value),
        }

        files: Dict[str, tuple] = {
            'x': (file_name, file_content, 'application/octet-stream'),
        }

        response: requests.Response = requests.post(self._host_graphql, data=data, files=files, cookies=self._cookies)

        response.raise_for_status()  # Ensure we got a successful response
        
        print(response.content)
        
        return response.json()

