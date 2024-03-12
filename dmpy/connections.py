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
        cookies = {
            'connect.sid': 's%3AZ3sB9YI3U6OeWVFbnFJT6ev1G5NxIkNy.Ba3VXdmo6Z4FmoOWdt3IIjRqYA1N0cGzm8outuejZg8'
        }
        headers = {
            'Authorization': "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJwdWJsaWNLZXkiOiItLS0tLUJFR0lOIFBVQkxJQyBLRVktLS0tLVxuTUlJQ0lqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FnOEFNSUlDQ2dLQ0FnRUExcnZiSnM0a0NaZGtBbmNDdDVNRVxudEZaaU1uZzhUL2loQmk4SUhTVDU4Z0QySm1RZ1EreHdzTlM2ZHZZNWpFcU5HWDhkOHBqUzF2MXUySEo4cGVuMFxuN3YxS1I3TXFQUVczQnZCSzVZT09WSG45MllhVE11eVMyRTgwaTREdk44L0lYVExiUjdRR0VYTkxJY042STZPd1xuVkJKZFY3V2dlMENqMWVnbVF3N09SZVNZUUoyU0ErSUdhSW9oU2RKZmZ3UUVrUWthZnVXc05XL2pScjM5TFY2Z1xuTjQwSTlzUzgzK1NGOTB6L2hkb3ZtTTFxc0FwVVFwZ3RWMHFFanllSjdWb3F4dGs3QllDSXIyNlh0ZGZaVU1lNFxuckJyb2xmZnllS2REcnZZUDBRU3dVZm9pTFh4dEdMek9BVmtJeG1rNnNyREh2VmpMN0hrVDRBVVM5czJXRnR3dlxuR2JwbmFVZ0lYZXR4ZUpxMnV3WDM4aGp2RUdpNm54WURka056VkdRZVlINXVNdTdFMXEyS1VpaGtGVlRTdFJuZVxuU3VJNUxocGpmRmdxbTdOblZNUEVWRHBnNHBkNy9KeGQ0SThIWUYzSlpHVTVpUStMOWNieGszTVlNOEhMc0ZRQlxudGRVSkF0bkpMTkU5RWczZ2I1Q0NFRW9haFZRQjNndTZLbHRTU0FIbGxxelZDVlJteUFITXF4OFltTWhtdWFsNFxuUmt6Q094amRRb2gxZzBvZGRNaGdTOXlUUWQwbHVXd2V2cURabk9na2xUL1R5MytyanNWLzkvMFIwM2pEZWZ4WlxuNkdRUGV5c0hhQnlER3ByL1M4aVdocVozS1k1WVVPWjc4Rk9ESGlxNGs3QzkreUxwYjJPQ0JJVVVNOGhBRE1seFxubDY3SUVKVWxVOFFZSm9xdGRUK0FWQlVDQXdFQUFRPT1cbi0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLVxuIiwiYXNzb2NpYXRlZFVzZXJJZCI6IjhhNTFiZGE3LTY0YjgtNDZhZi1iMDg3LTQzY2FhZDc0M2E4MSIsInJlZnJlc2hDb3VudGVyIjo1NzksIklzc3VlciI6IklERUEtRkFTVCBETVAiLCJpYXQiOjE3MDYyODk3NTgsImV4cCI6MTcwNjMwMTc1OH0.An4Erf6HLYYTOif88u5aaOa1owW7H77B0jQylmRTA5M8-wHzwu3u2BdARSMfFGqZsxjf5Ad40dQw4qSKnm9TFRzxyfft_8peT6Nh3C04BTc1DN9Rorg2usSrSimLWLvzs96z3smEGbdY2ZmwyNQPFvnyc-Z4Nb5daO6ngU5G4J0XTpE_NZofYFhgcBgsVl3KiIID_yfqT9m1aCfEF4bL4mWicJ0nVfpHa6eu3E1rKQ61EEBTUGmDXwtzbiymhuXWt3aBldP_tmpU_UwaqcrAdqDwoiMe11YTjhbnqW32TirkKsEdUS9oiPKYfv2EaYAd3htCkojr2Oej5dRCKwpU0g7F7OiRkkr84IZsZNaFaB9IIvPUattkhIlzmmn940q4CuCSjYuO1kEryimXc8xXI7X0dS_-Dmq8uklg6fl3wYYBylheU_CK-LE1uDwG508UO5iUuCwrRl1X6jb9RatXejTehxhIYDn7OpeZNZ22dP37i_7DZxw7YghJUn2IeZ_83FT2agC8ROM4xNHd2aa66T6zhG5QF-6hd9iwfBg8IkeBKtvsW8oJIhDjDHV8pJi0cZwkT7YhyPfw10RiKmtgO3Gvge4-wXHeAmpMcodgYFC8qWBq8yldTP21NOPQAVK7KYYEpYegQOsoAZEq0RbJTmn25dv8JHI7kdIC8y1lwSE"
        }
        response: requests.Response = requests.post('http://localhost:4200/graphql', data=data, files=files, headers=headers)
        response.raise_for_status()  # Ensure we got a successful response
        
        print(response.content)
        
        return response.json()

