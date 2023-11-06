from io import BytesIO
from dmpy.connections import DMPConnection
from dmpy.utils import get_file_type
from colorama import Fore, Style
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import json
import zipfile
import tarfile
import rarfile
import py7zr
from io import BytesIO, StringIO


def state():
    """
    Print current user info and studies can be accessed
    """
    # get the connection
    conn = DMPConnection()
    # get the whoami
    whoami = conn.graphql_request('whoami', None)
    if 'data' not in whoami:
        print(f"{Fore.LIGHTRED_EX}{Fore.RESET}")
        return
    print(f"User name: {Fore.LIGHTGREEN_EX}{whoami['data']['whoAmI']['username']}{Fore.RESET}")
    print(
        f"Name: {Fore.LIGHTGREEN_EX}{whoami['data']['whoAmI']['firstname']} {whoami['data']['whoAmI']['lastname']}{Fore.RESET}")
    print(f"Email: {Fore.LIGHTGREEN_EX}{whoami['data']['whoAmI']['email']}{Fore.RESET}")
    created_at = datetime.fromtimestamp(int(whoami['data']['whoAmI']['createdAt']) * 0.001, tz=timezone.utc)
    expires_at = datetime.fromtimestamp(int(whoami['data']['whoAmI']['expiredAt']) * 0.001, tz=timezone.utc)
    print(f"Account Created: {Fore.LIGHTGREEN_EX}{created_at}{Fore.RESET}")
    print(f"Account Expires: {Fore.LIGHTGREEN_EX}{expires_at}{Fore.RESET}")
    studies = whoami['data']['whoAmI']['access']['studies']
    if len(studies) == 0:
        print(
            f"{Fore.LIGHTRED_EX}You do not have access to any studies!{Fore.RESET}"
        )
    else:
        print(f"You have access to {len(studies)} studies:")
        for study in studies:
            print(
                f"{Fore.LIGHTCYAN_EX}{study['id']}{Fore.RESET} = "
                f"{Fore.YELLOW}{study['name']}{Fore.RESET}"
            )
    return studies


def list_files(
        study_id: str,
        participants: Optional[List[str]] = None,
        kinds: Optional[List[str]] = None,
        devices: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
):
    """
    List files in a study
    """

    def file_json_reformat(file_json):
        dtx: str = file_json["description"]
        description: Dict[str, Any] = json.loads(dtx)
        utt = file_json.get("uploadTime", None)
        if isinstance(utt, str):
            utt = int(utt)
        start_stamp = description.get("startDate", None)
        end_stamp = description.get("endDate", None)
        participant = description.get("participantId")
        if participants is not None and participant not in participants:
            return None
        device_id: Optional[str] = description.get("deviceId", None)
        if devices is not None and device_id not in devices:
            return None
        device_kind = device_id[0:3] if device_id is not None else None
        if kinds is not None and device_kind not in kinds:
            return None
        file_id = file_json["id"]
        if file_ids is not None and file_id not in file_ids:
            return None
        return {
            "fileId": file_id,
            "fileName": file_json.get("fileName"),
            "fileSize": file_json["fileSize"],
            "participantId": participant,
            "deviceKind": device_kind,
            "deviceId": device_id,
            "timeStart": datetime.fromtimestamp(start_stamp * 0.001).strftime(
                "%Y-%m-%d %H:%M:%S") if start_stamp is not None else None,
            "timeEnd": datetime.fromtimestamp(end_stamp * 0.001).strftime(
                "%Y-%m-%d %H:%M:%S") if end_stamp is not None else None,
            "timeUpload": datetime.fromtimestamp(utt * 0.001).strftime(
                "%Y-%m-%d %H:%M:%S") if utt is not None else None,
            "stampStart": start_stamp,
            "stampEnd": end_stamp,
            "stampUpload": utt,
            "uploadedBy": file_json.get("uploadedBy"),
            "studyId": file_json.get("studyId"),
        }

    conn = DMPConnection()
    variables = {
        "studyId": study_id,
    }
    all_files = conn.graphql_request("files", variables)
    if 'data' not in all_files:
        print(f"{Fore.LIGHTRED_EX}error to list files in study: {study_id}{Fore.RESET}")
        return
    study = all_files['data']['getStudy']
    files = study['files']
    files2 = [file_json_reformat(f) for f in files if file_json_reformat(f) is not None]
    return files2


def get_file_content(file_id: str, stream: bool = True, decode: str = None):
    conn = DMPConnection()
    if decode:
        return conn.get_file(file_id, stream=stream).decode(decode)
    return conn.get_file(file_id, stream=stream)


def archive_preview(file_id: str, file_name: str):
    file_type = get_file_type(file_name)
    file_stream = get_file_content(file_id)
    compressed_data = BytesIO(file_stream)
    if not file_type or file_type not in ["zip", "tar.gz", "rar", "7z"]:
        print("Not an archive")
        return "Not an archive"
    else:
        if file_type == 'zip':
            with zipfile.ZipFile(compressed_data) as zf:
                print("ZIP file structure:")
                for file_info in zf.infolist():
                    print(file_info.filename)
                return [file_info.filename for file_info in zf.infolist()]
        elif file_type == 'tar.gz':
            with tarfile.open(fileobj=compressed_data, mode='r:gz') as tar:
                print("Tarred GZ file structure:")
                for tar_info in tar:
                    print(tar_info.name)
                return [tar_info.filename for tar_info in tar]
        elif file_type == 'rar':
            with rarfile.RarFile(compressed_data) as rf:
                print("RAR file structure:")
                for rar_info in rf.infolist():
                    print(rar_info.filename)
                    return [rar_info.filename for rar_info in rf.infolist()]
        elif file_type == '7z':
            with py7zr.SevenZipFile(compressed_data, mode='r') as z:
                print("7Z file structure:")
                for name in z.getnames():
                    print(name)
                    return [name for name in z.getnames()]

    

def stream_text_from_archive(file_id, file_name):
    file_type = get_file_type(file_name)
    file_stream = get_file_content(file_id)
    compressed_data = BytesIO(file_stream)
    if file_type == 'zip':
        with zipfile.ZipFile(compressed_data) as zf:
            for file_info in zf.infolist():
                if file_info.filename.endswith('/'):
                    continue
                with zf.open(file_info, 'r') as file:
                    try:
                        data = StringIO(file.read().decode('utf-8'))
                        yield file_info.filename, data
                    except UnicodeDecodeError:
                        print(f'Could not decode file {file_info.filename} in UTF-8')
    elif file_type == 'tar.gz':
        with tarfile.open(fileobj=compressed_data, mode='r:gz') as tar:
            for tar_info in tar:
                if tar_info.isfile():
                    file = tar.extractfile(tar_info)
                    try:
                        data = StringIO(file.read().decode('utf-8'))
                        yield tar_info.name, data
                    except UnicodeDecodeError:
                        print(f'Could not decode file {tar_info.name} in UTF-8')
    elif file_type == '7z':
        with py7zr.SevenZipFile(compressed_data, mode='r') as z:
            for file_info in z.getnames():
                if file_info.filename.endswith('/'):
                    continue
                try:
                    with z.read(file_info) as file:
                        data = StringIO(file.read().decode('utf-8'))
                        yield file_info, z.data
                except UnicodeDecodeError:
                    print(f'Could not decode file {file_info} in UTF-8')
    elif file_type == 'rar':
        with rarfile.RarFile(compressed_data) as rf:
            for file_info in rf.infolist():
                if file_info.filename.endswith('/'):
                    continue
                with rf.open(file_info, 'r') as file:
                    try:
                        data = StringIO(file.read().decode('utf-8'))
                        yield file_info.filename, data
                    except UnicodeDecodeError:
                        print(f'Could not decode file {file_info.filename} in UTF-8')

def stream_text_from_specific_archive_file(file_id, file_name, sub_file_name: str = None):
    file_type = get_file_type(file_name)
    file_stream = get_file_content(file_id)
    compressed_data = BytesIO(file_stream)
    if file_type == 'zip':
        with zipfile.ZipFile(compressed_data) as zf:
            for file_info in zf.infolist():
                if file_info.filename != sub_file_name:
                    continue
                if file_info.filename.endswith('/'):
                    continue
                with zf.open(file_info, 'r') as file:
                    try:
                        data = StringIO(file.read().decode('utf-8')).getvalue()
                        return file_info.filename, data
                    except UnicodeDecodeError:
                        return (f'Could not decode file {file_info.filename} in UTF-8')
    elif file_type == 'tar.gz':
        with tarfile.open(fileobj=compressed_data, mode='r:gz') as tar:
            for tar_info in tar:
                if tar_info.name != sub_file_name:
                    continue
                if tar_info.isfile():
                    file = tar.extractfile(tar_info)
                    try:
                        data = StringIO(file.read().decode('utf-8')).getvalue()
                        return tar_info.name, data
                    except UnicodeDecodeError:
                        return (f'Could not decode file {tar_info.name} in UTF-8')
    elif file_type == '7z':
        with py7zr.SevenZipFile(compressed_data, mode='r') as z:
            for file_info in z.getnames():
                if file_info.filename != sub_file_name:
                    continue    
                try:
                    with z.read(file_info) as file:
                        data = StringIO(file.read().decode('utf-8')).getvalue()
                        return file_info, z.data
                except UnicodeDecodeError:
                    return (f'Could not decode file {file_info.filename} in UTF-8')
    elif file_type == 'rar':
        with rarfile.RarFile(compressed_data) as rf:
            for file_info in rf.infolist():
                if file_info.filename != sub_file_name:
                    continue
                with rf.open(file_info, 'r') as file:
                    try:
                        data = StringIO(file.read().decode('utf-8')).getvalue()
                        return file_info.filename, data
                    except UnicodeDecodeError:
                        print(f'Could not decode file {file_info.filename} in UTF-8')

    return sub_file_name


def upload_data(study_id: str, file_name: str, file_content: bytes, participant_id: str, device_id: str,
                start_date: int, end_date: int):
    conn = DMPConnection()
    variables = {
        'studyId': study_id,
        'description': json.dumps(
            {
                "participantId": participant_id,
                "deviceId": device_id,
                "startDate": start_date,
                "endDate": end_date,
            }
        )
    }
    try:
        response = conn.upload_file(file_name, file_content, variables)
        if "error" in response:
            print(f"{Fore.LIGHTRED_EX}Error uploading file {file_name}: {response['error']}{Fore.RESET}")
            return
        print(f"{Fore.LIGHTGREEN_EX}File {file_name} uploaded successfully{Fore.RESET}")

        file_id = response['data']['uploadFile']['id']
        return file_id

    except Exception as e:
        print(f"{Fore.LIGHTRED_EX}Error uploading file {file_name}: {e}{Fore.RESET}")


def get_study_fields(study_id: str, versionId=''):
    conn = DMPConnection()
    variables = {
        "studyId": study_id,
    }
    if versionId == None:
        variables['versionId'] = None
    study_fields = conn.graphql_request('study_fields', variables)
    return study_fields['data']['getStudyFields']


def create_new_field(study_id: str, field_id: str, field_name: str, data_type: str, possible_values: List = None,
                     unit: str = None, comments: str = None, table_name: str = None):
    if data_type == "cat" and possible_values is None:
        raise Exception("possible values needed when data_type is 'cat'")
    field_input = {
        "fieldId": field_id,
        "fieldName": field_name,
        "dataType": data_type
    }
    if possible_values:
        field_input["possibleValues"] = possible_values
    if unit:
        field_input["unit"] = unit
    if comments:
        field_input["comments"] = comments
    if table_name:
        field_input["tableName"] = table_name
    variables = {
        "studyId": study_id,
        "fieldInput": field_input
    }
    conn = DMPConnection()
    response = conn.graphql_request('create_field', variables)
    if 'errors' in response:
        raise Exception(response['errors'])
    return response['data']['createNewField']


def get_data_records(study_id: str, 
                     field_ids: List[str] = None, 
                     data_format: str = None, 
                     version_id: str = '0',
                     table_requested: str = None):
    conn = DMPConnection()
    variables = {
        "studyId": study_id,
        "queryString": {
            "data_requested": field_ids,
            "format": "raw",
            "new_fields": None,
            "cohort": None,
        }
    }

    if data_format:
        variables["queryString"]["format"] = data_format
    if not version_id:
        variables["versionId"] = None
    if version_id == '-1':
        variables["versionId"] = version_id
    if table_requested:
        variables["queryString"]["table_requested"] = table_requested

    data_records = conn.graphql_request('data_records', variables)
    return data_records['data']['getDataRecords']["data"]


def upload_data_in_array(study_id: str, data: List[dict]):
    conn = DMPConnection()
    variables = {
        'studyId': study_id,
        'data': data
    }
    try:
        response = conn.graphql_request('upload_data_in_array', variables)
        # if "error" in response:
        #     print(f"{Fore.LIGHTRED_EX}Error uploading data: {response['error']}{Fore.RESET}")
        # else:
        #     print(f"{Fore.LIGHTGREEN_EX}Data uploaded successfully{Fore.RESET}")
        return response
    except Exception as e:
        print(f"{Fore.LIGHTRED_EX}Error uploading data: {e}{Fore.RESET}")

def delete_study_field(study_id: str, field_id: str):
    conn = DMPConnection()
    variables = {
        "studyId": study_id,
        "fieldId": field_id
    }
    response = conn.graphql_request('deleteField', variables)
    print(response)
    return response['data']['deleteField']