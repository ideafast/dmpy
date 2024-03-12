from io import BytesIO
import math
from dmpy.connections import DMPConnection
from dmpy.utils import get_file_type
from colorama import Fore, Style
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
import json
# import zipfile
# import tarfile
# import rarfile
# import py7zr
from io import BytesIO, StringIO
import pandas as pd
import copy
from datetime import datetime
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
    return stream_data_from_archive(file_id, file_name, data_type='text')


def stream_data_from_archive(file_id, file_name, data_type='text'):
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
                        if data_type == 'binary':
                            data  = data = file.read()  # Read file as binary data
                        elif data_type == 'text':
                            data = StringIO(file.read().decode('utf-8'))
                        yield file_info.filename, data
                    except UnicodeDecodeError:
                        try:
                            file.seek(0)  # Reset file pointer
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            print(f"Failed to decode file {file_info.filename} in UTF-8 or ISO-8859-1: {e}")

    elif file_type == 'tar.gz':
        with tarfile.open(fileobj=compressed_data, mode='r:gz') as tar:
            for tar_info in tar:
                if tar_info.isfile():
                    file = tar.extractfile(tar_info)
                    try:
                        if data_type == 'binary':
                            data  = data = file.read()  # Read file as binary data
                        elif data_type == 'text':
                            data = StringIO(file.read().decode('utf-8'))
                        yield tar_info.name, data
                    except UnicodeDecodeError:
                        try:
                            file.seek(0)  # Reset file pointer
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            print(f"Failed to decode file {file_info.filename} in UTF-8 or ISO-8859-1: {e}")
    elif file_type == '7z':
        with py7zr.SevenZipFile(compressed_data, mode='r') as z:
            for file_info in z.getnames():
                if file_info.filename.endswith('/'):
                    continue
                try:
                    with z.read(file_info) as file:
                        if data_type == 'binary':
                            data  = data = file.read()  # Read file as binary data
                        elif data_type == 'text':
                            data = StringIO(file.read().decode('utf-8'))
                        yield file_info, z.data
                except UnicodeDecodeError:
                        try:
                            file.seek(0)  # Reset file pointer
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            print(f"Failed to decode file {file_info.filename} in UTF-8 or ISO-8859-1: {e}")
    elif file_type == 'rar':
        with rarfile.RarFile(compressed_data) as rf:
            for file_info in rf.infolist():
                if file_info.filename.endswith('/'):
                    continue
                with rf.open(file_info, 'r') as file:
                    try:
                        if data_type == 'binary':
                            data = file.read()  # Read file as binary data
                        elif data_type == 'text':
                            data = StringIO(file.read().decode('utf-8'))
                        yield file_info.filename, data
                    except UnicodeDecodeError:
                        try:
                            file.seek(0)  # Reset file pointer
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            print(f"Failed to decode file {file_info.filename} in UTF-8 or ISO-8859-1: {e}")

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
                        try:
                            file.seek(0)
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            return (f'Could not decode file {file_info.filename} in UTF-8 or ISO-8859-1')
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
                        try:
                            file.seek(0)
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            return (f'Could not decode file {file_info.filename} in UTF-8 or ISO-8859-1')
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
                        try:
                            file.seek(0)
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            return (f'Could not decode file {file_info.filename} in UTF-8 or ISO-8859-1')
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
                        try:
                            file.seek(0)
                            data = StringIO(file.read().decode('ISO-8859-1'))
                            yield file_info.filename, data
                        except Exception as e:
                            return (f'Could not decode file {file_info.filename} in UTF-8 or ISO-8859-1')

    return sub_file_name


def upload_data(study_id: str, file_name: str, file_content: bytes, participant_id: str, device_id: str,
                start_date: int, end_date: int):
    conn = DMPConnection()
    variables = {
        'studyId': study_id,
        'file': None,
        'description': json.dumps({
                "participantId": participant_id,
                "deviceId": device_id,
                "startDate": start_date * 1000,
                "endDate": end_date * 1000,
            }
        )
    }
    try:
        response = conn.upload_file(file_name, file_content, variables)
        print("Raw server response:",  response)

        if "error" in response or "errors" in response:
            print(f"{Fore.LIGHTRED_EX}Error uploading file {file_name}: {response['error']}{Fore.RESET}")
            print(response["errors"])
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


# the following functions are used temporarily
def fetch_adam_data(study_id: str, domain: str):
    """
    Fetches and returns data related to the specified study and domain.

    Parameters:
    study_id (str): The unique identifier of the study.
    domain (str): The domain from which to fetch data. Available options:
            ADDI

    Returns:
    Data related to the study and domain. The type and structure of the data
    depend on the domain specified.
    """
    ATUP_mapping = {
        "1": "Start of TUP 1",
        "2": "End of TUP 1",
        "3": "Start of TUP 2",
        "4": "End of TUP 2",
        "5": "Start of TUP 3",
        "6": "End of TUP 3",
        "7": "Start of TUP 4",
        "8": "End of TUP 4",
    }

    derived_fields = ["1144", "1167", "derived_Demographics_Region", "derived_Demographics_Country", "derived_Demographics_Country", "1168", "dataset_id", "derived_Demographics_BMI", "1145", "1151", "derived_Demographics_Age", "derived_Demographics_AgeCat", "1148", "1146", "1141", "1143", "NONE", "derived_FACITF_score", "derived_fVAS_fvas", "derived_mMFS_score", "695", "derived_ESS_score", "derived_sqVAS_sqvas", "derived_MOSSS_SLPD4", "derived_MOSSS_SLPSNR1", "derived_MOSSS_SLPSOB1", "derived_MOSSS_SLPA2", "derived_MOSSS_SLPS3", "derived_MOSSS_SLP6", "derived_MOSSS_SLP9", "derived_MOSSS_SLPQRAW", "derived_MOSSS_SLPOP1", "1241", "1242", "1249", "1250", "1235", "1236", "NONE", "derived_MDSUPDRSII_mdsupdrs2_score", "derived_MDSUPDRSII_disease_severity_cat_id", "derived_MDSUPDRSIII_mdsupdrs3_score", "derived_MDSUPDRSIII_disease_severity_cat_id", "derived_UHDRS_tfc_score", "derived_UHDRS_disease_severity_cat_id", "derived_ESSDAI_ESSDAI_score", "derived_ESSDAI_disease_severity_cat_id", "derived_SLEDAI2K_SLEDAI_score", "derived_SLEDAI2K_disease_severity_cat_id", "derived_DiseaseActivityScore_DAS28_CRP", "derived_DiseaseActivityScore_disease_severity_cat_id", "derived_LabParameters_calprotectin", "derived_LabParameters_disease_severity_cat_id","derived_FACITF_DateofAssessment", "derived_fVAS_DateofAssessment", "derived_mMFS_DateofAssessment", "derived_KSS_DateofAssessment", "derived_ESS_DateofAssessment","derived_sqVAS_DateofAssessment","derived_MOSSS_DateofAssessment","derived_PGIF_DateofAssessment","derived_PGISQ_DateofAssessment","derived_PGIDS_DateofAssessment",
            "derived_SubjectgroupCharacterisation_timesincediagnosis", "derived_TUP1_start_date", "derived_TUP2_start_date","derived_TUP3_start_date","derived_TUP4_start_date","derived_TUP1_stop_date","derived_TUP2_stop_date","derived_TUP3_stop_date","derived_TUP4_stop_date", "derived_Demographics_DateofAssessment"
        ]

    default_version = None
    if domain == 'ADDI':
        addi_data = get_data_records(
            study_id=study_id,
            field_ids=["derived_ADDI"],
            version_id=default_version
        )
        dataset_id_data = get_data_records(
            study_id=study_id,
            field_ids=['dataset_id'],
            version_id=default_version
        )
        dataframe = []
        desired_order = ['USUBJID', 'STUDYID', 'ANALYSISSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'ATM', 'TIMING', 'AVAL', 'AVALC', 'PARAM', 'PARAMCD']
        dataframe.append(desired_order)
        param_mapping = {
            'ACTIVI01': "Where were you mainly in the last hour, inside, outside, motorised transport (bus, car, train?)",
            'ACTIVI02': "Were you mainly doing (employed) work or studies, yes, no.",
            'ACTIVI03': "Were you mostly on a break during your last hour of (paid) work or studies, yes, no.",
            'ACTIVI04': "Mark on the line the level of physical activity during this time, 0 = low physical activity (desk work), 100 = High physical activity (physical work)",
            'ACTIVI05': "What activity have you mainly done in the last hour, Housekeeping/Gardening",
            'ACTIVI06': "What activity have you mainly done in the last hour, Shopping, Walking, Sports incl. cycling, Gardening, Relaxing, Social interaction/events",
            'DIARY01': "How fatigued to you feel overall, 0 = Not at all fatigued, 100 = worst possible fatigued",
            'DIARY02': "How fatigued to you feel physically, 0 = Not at all fatigued physically, 100 = worst possible fatigued physically",
            'DIARY03': "How fatigued to you feel mentally, 0 = Not at all fatigued mentally, 100 = worst possible fatigued mentally",
            'DIARY04': "How anxious do you feel, 0 = No at all anxious, 100 = worst possible anxiousness",
            'DIARY05': "How low is your mood, 0 = My mood is not low at all, 100 = Lowest possible mood",
            'DIARY06': "How much pain are you having, 0 = No pain at all, 100 = Worst possible pain",
            'DIARY07': "How was your sleep last night 0 = Best possible sleep, 100 = Worst possible sleep",
            'DIARY08': "Please choose the response below that best describes your sleep quality last night, 1 = No sleep problems, 2 = Mild sleep problems, 3 = Moderate sleep problems, 4 = Severe sleep problems, 5 = Very severe sleep problems",
            'DIARY09': "Please choose the response below that best describes the overall change in your sleep quality today compared to yesterday, 1= Very much improved, 2 = Much improved, 3 = Minimally improved, 4 = No change, 5 ? Minimally worse, 6 = Much worse, 7 = Very much worse",
            'KSS': "How do you feel at the moment, where 1 = extremely alert, 2 = very alert, 3 = alert, 4 = rather alert, 5 = neither alert nor sleepy, 6 = some signs of sleepiness, 7 = sleepy, but no effort to keep awake, 8 = sleepy, but some effort to keep awake,",
            'MOBILY01': "How do you rate your mobility with regard to stiffness, rigidity and/or slowness that affects your daily life within this last hour, 0 =Normal, -1 = Mild impaired mobility, -2 = Moderately impaired mobility, -3 Severely impaired mobility",
            'MOBILY02': "How do you rate your mobility with regard to involuntary extra movements that affects your daily life within this last hour, 0 = Normal, 1 = Mild dyskinesia, 2 = Moderate dyskinesia, 3 = Severe dyskinesia",
            'PGISCE1': "Please choose the response below that best describes the severity of your overall fatigue in the past 24 hours, 1 = No fatigue, 2 ? Mild fatigue, 3 = Moderate fatigue, 4 = Severe fatigue, 5 = Very severe fatigue",
            'PGISCE2': "Please choose the response below that best described the change in your overall fatigue today compared to yesterday, 1= Very much improved, 2 = Much improved, 3 = Minimally improved, 4 = No change, 5 ? Minimally worse, 6 = Much worse, 7 = Very much worse",
            'PGISCE3': "Please choose the response below that best describes the severity of your daytime sleepiness in the past 24 hours, 1 = No daytime sleepiness, 2 = Mild daytime sleepiness, 3 = Moderate daytime sleepiness, 4 = Severe daytime sleepiness, 5 = Very severe daytime sleepiness",
            'PGISCE4': "Please choose the response below that best describes the change in your daytime sleepiness today compared to yesterday, 1= Very much improved, 2 = Much improved, 3 = Minimally improved, 4 = No change, 5 ? Minimally worse, 6 = Much worse, 7 = Very much worse"
        }

        for subjectId in addi_data:
            for visitId in addi_data[subjectId]:
                if visitId == '0':
                    continue
                tmp = [subjectId, 'IDEAFAST COS']
                if dataset_id_data.get(subjectId, {}).get(visitId):
                    if dataset_id_data[subjectId][visitId]['dataset_id'] == '1':
                        tmp.append('ISA')
                    elif dataset_id_data[subjectId][visitId]['dataset_id'] == '2':
                        tmp.append('ESA')
                    else:
                        tmp.append('')
                else:
                    tmp.append('')
                tmp.append(str(visitId))
                tmp.append('Visit ' + str(visitId))
                tmp.append('TUP ' + str(math.ceil(int(visitId) / 2)))
                tmp.append(ATUP_mapping[str(visitId)])

                # print(addi_data[subjectId][visitId], type(addi_data[subjectId][visitId]))
                data_clip = json.loads(json.loads(addi_data[subjectId][visitId]['derived_ADDI']).replace("'", '"'))
                # print(type(data_clip), data_clip)
                for item in data_clip:
                    tmp1 = copy.deepcopy(tmp)
                    tmp1.append(item['ADT'])
                    tmp1.append(item['ATM'])
                    tmp1.append(item['TIMING'])
                    for key in list(param_mapping.keys()):
                        if key in item:
                            tmp2 = copy.deepcopy(tmp1)
                        else:
                            continue
                        tmp2.append(item[key])
                        tmp2.append(item[str(key)])
                        tmp2.append(param_mapping[key])
                        tmp2.append(key)
                        dataframe.append(tmp2)
        df = pd.DataFrame(dataframe)
        return df
    elif domain == 'ADPRO':
        desired_order = ['USUBJID', 'STUDYID', 'ANALYSISSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'ADY', 'AVAL', 'AVALC', 'FORMID', 'FORMNAME', 'PARAM', 'PARAMCD']
        format1 = "%Y-%m-%dT%H:%M:%S.%f"
        format2 = "%Y-%m-%d %H:%M:%S"
        adpro_data = get_data_records(
            study_id=study_id,
            field_ids=derived_fields,
            data_format="standardized-cdisc:adam:adpro",
            version_id="-1"
        )


        for item in adpro_data['ADPRO']:
            for key in desired_order:
                if key not in item:
                    item[key] = ''
        tup_data = get_data_records(
            study_id=study_id,
            field_ids=['derived_TUP1_start_date', 'derived_TUP2_start_date', 'derived_TUP3_start_date', 'derived_TUP4_start_date'],
            version_id="-1"
        )
        for item in adpro_data['ADPRO']:
            subjectId = item['USUBJID']
            visitId = item['VISITNUM']
            ADT = item['ADT']
            if subjectId and visitId and ADT and subjectId in tup_data:
                tup_key = 'derived_TUP' + str(int(math.ceil(int(visitId)/2))) + '_start_date'
                result = 'NA'
                if tup_key in tup_data[subjectId]['0']:
                    time1_dt = datetime.strptime(ADT, format1)
                    time2_dt = datetime.strptime(tup_data[subjectId]['0'][tup_key], format2)
                    # Calculate the difference
                    if time1_dt < time2_dt:
                        result = "Invalid"
                    else:
                        difference = time1_dt - time2_dt
                        # You can format the difference as needed
                        result = str(difference)
            item['ADY'] = result
        df = pd.DataFrame(adpro_data['ADPRO'])
        return df[desired_order]
    elif domain == 'ADCL':
        desired_order = ['USUBJID','STUDYID','ANALYSISSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'AVAL', 'AVALC', 'FORMID', 'FORMNAME', 'PARAM', 'PARAMCD']
        adcl_data = get_data_records(
            study_id=study_id,
            field_ids=derived_fields,
            data_format="standardized-cdisc:adam:adcl",
            version_id="-1"
        )
        for item in adcl_data['ADCL']:
            for key in desired_order:
                if key not in item:
                    item[key] = ''
        df = pd.DataFrame(adcl_data['ADCL'])
        return df[desired_order]
    elif domain == 'ADSL':
        desired_order = ['USUBJID','SITE','REGION','COUNTRY','STUDYID','COHORT','DEMOCOLLDTC','ANALYSISSET','BMI','HEIGHT','WEIGHT','AGE','AGEU','AGECAT','GENDER','OCCUPATION','EDUCATION','ETHNICITY','TIMESINCEDIAG','TUP1DT','TUP1TZ','TUP2DT','TUP2TZ','TUP3DT','TUP3TZ','TUP4DT','TUP4TZ']
        adsl_data = get_data_records(
            study_id=study_id,
            field_ids=derived_fields,
            data_format="standardized-cdisc:adam:adsl",
            version_id="-1"
        )
        for item in adsl_data['ADSL']:
            for key in desired_order:
                if key not in item:
                    item[key] = ''
        df = pd.DataFrame(adsl_data['ADSL'])
        return df[desired_order]
    
