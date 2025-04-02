"""
    This file provides functions that call the API directly.
"""
# pylint: disable=broad-exception-caught

from typing import Optional, Any
import json
import os
import urllib.parse
import requests
from dmpy.utils import *
from dmpy.utils import load_cookie_from_file, load_host_from_file
import time
from concurrent.futures import ThreadPoolExecutor
import threading

class DMPConnectiontRPC:
    """
        This class implements the basic Python API wrapper of the DMP API.
    """
    def __init__(self, token=None):
        if os.environ.get('DMP_URL'):
            host = os.environ.get('DMP_URL')
        else:
            host = load_host_from_file()
            if host is None:
                host = 'https://data.ideafast.eu'
            else:
                host = f'https://{host}'
        self.host = host + '/trpc'
        # self.token = token
        # self.validate_token()
        if os.environ.get('DMP_COOKIE'):
            cookie = os.environ.get('DMP_COOKIE')
        else:
            cookie = load_cookie_from_file()
        self._cookies = {"connect.sid": cookie}
        # self.get_studies()

    def send_query(self, query_name, parameters):
        """
            Send a tRPC api via https query.
        """
        parent = os.path.dirname(os.path.abspath(__file__))
        queries = read_json(os.path.join(parent, 'queries.json'))
        found_item = next((item for item in queries if item["endpoint"] == query_name), None)
        if not found_item:
            return 'Query not recognized.'
        try:
            if found_item['method'] == 'GET':
                response = requests.request(found_item['method'], self.host + '/' + query_name + '?input=' + urllib.parse.quote(json.dumps(parameters)), 
                cookies=self._cookies, data=parameters, timeout=300).json()
                if 'result' in response and 'data' in response['result']:
                    return response['result']['data']
                else:
                    # print('Unable to query.')
                    # print('Error: ', response.get('error', {}.get('message')))
                    return response
            elif found_item['method'] == 'POST':
                response = requests.request(found_item['method'], self.host + '/' + query_name,
                cookies=self._cookies, json=parameters, timeout=300).json()
                if 'result' in response and 'data' in response['result']:
                    return response['result']['data']
                else:
                    # print('Unable to query.')
                    # print('Error: ', response.get('error', {}.get('message')))
                    return response
        except Exception as e:
            print(f"Unable to query. {e}")
            return False

    def validate_token(self):
        """
            Validate the token by requesting a whoAmI query.
        """
        try:
            user = self.send_query('user.whoAmI', {})
            if user:
                self.user = user
            else:
                print('Token not recognized.')
        except Exception as e:
            print(f"Token not recognized. {e}")

    def who_am_i(self):
        """
            Python wrapper for user.whoAmI.
        """
        return self.send_query('user.whoAmI', {})

    def get_studies(self, study_id=None):
        """
            Python wrapper for study.getStudies.
        """
        if study_id:
            return self.send_query('study.getStudies', {"studyId": study_id})
        else:
            studies = self.send_query('study.getStudies', {})
            return studies
            
    def get_study_data(self, study_id, field_ids, version_id, max_workers=4):
        """
            Python wrapper for data.getStudyData.
        """
        refactored_version_ids = None
        study = self.get_studies(study_id)[0]
        if version_id is None:
            refactored_version_ids = [study['dataVersions'][i]['id'] for i in range(len(study['dataVersions']))] + [None]
        elif not version_id or version_id == '-1':
            refactored_version_ids = [study['dataVersions'][i]['id'] for i in range(len(study['dataVersions']))]
        else:
            refactored_version_ids = []
            for el in study['dataVersions']:
                refactored_version_ids.append(el['id'])
                if el['tag'] == version_id:
                    break
        
        responses = self.send_query('data.getStudyData', {"studyId": study_id, "fieldIds": field_ids, "versionId": refactored_version_ids})
        return responses['raw'] if 'raw' in responses else responses
        
    def get_data_latest(self, study_id, field_ids ):
        """
            Python wrapper for data.getStudyDataLatest.
        """
        responses =  self.send_query('data.getStudyData', {"studyId": study_id, "fieldIds": field_ids})
        return responses['raw'] if 'raw' in responses else responses
        
    def get_files(self, study_id, version_id='-1', field_ids=None):
        """
            Python wrapper for data.getFiles.
        """
        refactored_version_ids = None
        study = self.get_studies(study_id)[0]
        if version_id is None:
            data_versions = study['dataVersions']
            refactored_version_ids = [d['id'] for d in data_versions]
            refactored_version_ids.append(None)
        elif (not version_id) or (version_id == '-1'):
            refactored_version_ids = [el['id'] for el in study['dataVersions']]
        else:
            tmp = []
            for version in study['dataVersions']:
                if version['tag'] == version_id:
                    break
                else:
                    tmp.append(version['id'])
            refactored_version_ids = tmp
        parameters = {
            'studyId': study_id,
            'readable': True,
            'versionId': refactored_version_ids
        }
        if field_ids:
            parameters['fieldIds'] = field_ids
        response = self.send_query('data.getFiles', parameters)
        return response


    def get_files_latest(self, study_id):
        """
            Python wrapper for data.getFiles.
        """
        return self.send_query('data.getFilesLatest', {"studyId": study_id})

    def get_study_fields(self, study_id, version_id):
        """
            Python wrapper for data.getStudyFields.
        """
        refactored_version_ids = None
        study = self.get_studies(study_id)[0]
        if version_id is None:
            data_versions = study['dataVersions']
            refactored_version_ids = [d['id'] for d in data_versions]
            refactored_version_ids.append(None)
        elif (not version_id) or (version_id == '-1'):
            refactored_version_ids = [el['id'] for el in study['dataVersions']]
        else:
            tmp = []
            for version in study['dataVersions']:
                if version['tag'] == version_id:
                    break
                else:
                    tmp.append(version['id'])
            refactored_version_ids = tmp

        return self.send_query('data.getStudyFields', {"studyId": study_id, "versionId": refactored_version_ids})
    

    # mutation
    def create_study_field(self, study_id, field_name, field_id, data_type, description: Optional[str] = None , categorical_options: Optional[str] = None, unit: Optional[str] = None, comments: Optional[str] = None, verifier: Optional[str] = None, properties = None, metadata = None):
        """
            Python wrapper for data.createStudyField.
        """
        variables = {
            "studyId": study_id,
            "fieldName": field_name,
            "fieldId": field_id,
            "dataType": data_type,
            "properties": [
                {
                    "name": "subjectId",
                    "required": True
                },
                {
                    "name": "visitId",
                    "required": True
                }
            ]
        }
        if description:
            variables['description'] = description
        if categorical_options:
            variables['categoricalOptions'] = categorical_options
        if unit:
            variables['unit'] = unit
        if comments:
            variables['comments'] = comments
        if verifier:
            variables['verifier'] = verifier
        if metadata:
            variables['metadata'] = metadata
        if properties:
            variables['properties'] = properties
        return self.send_query('data.createStudyField', variables)
    
    def delete_study_field(self, study_id, field_id):
        """
            Python wrapper for data.deleteStudyField.
        """
        return self.send_query('data.deleteStudyField', {"studyId": study_id, "fieldId": field_id})

    def delete_data(self, study_id, field_id, properties):
        """
            Python wrapper for data.deleteData.
        """
        return self.send_query('data.deleteData', {"studyId": study_id, "fieldId": field_id, "properties": properties})
    
    def upload_study_data(self, study_id, data):
        """
            Python wrapper for data.uploadStudyData.
        """
        return self.send_query('data.uploadStudyData', {"studyId": study_id, "data": data})

    # file
    def upload_study_file_data(self, study_id, field_id, properties: Optional[Any], file_name, file_content):
        """
            Python wrapper for data.uploadStudyFileData.
        """
        try:
            response = requests.request('POST', self.host + '/' + 'data.uploadStudyFileData', 
            cookies=self._cookies,
            data={
                "studyId": study_id,
                "fieldId": field_id,
                "properties": properties
            }, files=[(
                'file', (file_name, file_content)
            )]).json()
            if 'result' in response and 'data' in response['result']:
                return response['result']['data']
            else:
                print(f"Unable to query. {str(response)}")
                return False
        except Exception as e:
            print(f'Unable to query. {e}')
            return False 

    def get_file(self, file_id, stream=True):
        """
            Python wrapper for file.getFile.
        """
        url = f'{self.host[:-5]}/file/{file_id}'
        response = requests.get(url,  cookies=self._cookies, stream=stream)
        # print(url, self._cookies)
        if response.status_code != 200:
            raise Exception(f'Failed to download file {file_id}: {response.text}')
        return response.content


        
