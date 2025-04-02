import copy
import json
import math
from dmpy.connect import DMPConnectiontRPC
from colorama import Fore, Style
from typing import List, Dict, Optional, Any
import time
from datetime import datetime, timezone
from io import BytesIO, StringIO
from copy import deepcopy
import zipfile
import tarfile
from dmpy.utils import *
import rarfile
import py7zr
import pandas as pd
import multiprocessing as mp
from functools import partial
import numpy as np

def state():
    conn = DMPConnectiontRPC()
    studies = conn.get_studies()
    print(f"Connected to {Fore.LIGHTCYAN_EX}{len(studies)}{Fore.RESET} studies:")
    print(f"Connected to {Fore.LIGHTCYAN_EX}{len(studies)}{Fore.RESET} studies:")
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

def list_files(
        study_id: str,
        participants: Optional[List[str]] = None,
        kinds: Optional[List[str]] = None,
        devices: Optional[List[str]] = None,
        file_ids: Optional[List[str]] = None,
        version_id = '-1'
):
    conn = DMPConnectiontRPC()
    kinds_mapping = {
        'AX6': 'Axivity',
        'BVN': 'Biovotion',
        'BTF': 'Byteflies',
        'MMM': 'McRoberts',
        'DRM': 'Dreem',
        'VTP': 'VitalPatch',
        'BED': 'VTT Bed Sensor',
        'YSM': 'ZKOne',
        'MBT': 'Mbient',
        'IDE': 'German Interview Transcripts',
        'IEN': 'English Interview Transcripts',
        'INL': 'Dutch Interview Transcripts',
        'TEQ': 'Technology Experience Questionnaire',
        'PSG': 'PSG Study Polysomnography Data',
        'PSR': 'PSG raw data',
        'PSM': 'PSG meta data',
        'SMA': 'Stress Monitor App',
        'TFA': 'ThinkFast App',
        'SMQ': 'Stress Monitor App Questionnaire',
        'VIR': 'Virtual device type',
        'CAN': 'Cantab App',
        'TUP': 'Cantab TUP data',
        'WLD': 'Wildkey App',
        'SOC': 'Wildkey Social App',
        'SLP': 'Derived BED Sleep Features',
        'STS': 'Derived AX6 Kinematic Features',
        'COG': 'Derived CAN Cognitive Performance Metrics',
        'WKT': 'Derived WLD Typing Features',
        'WKS': 'Derived SOC Social Features',
        'HRV': 'Derived VTP HRV Features',
        'VIT': 'Derived VTP Basic Features',
        'GVA': 'Derived AX6 Gait Features',
        'MCR': 'Derived McRoberts Classification',
        'POE': 'Participant Experiences Opinions'
    }

    if kinds:
        refactored_kinds = []
        for kind in kinds:
            if kind in list(kinds_mapping.keys()):
                refactored_kinds.append('Device_' + '_'.join(kinds_mapping[kind].split(' ')))
            else:
                refactored_kinds.append(kind)
        files = conn.get_files(
            study_id,
            version_id,
            refactored_kinds
        )
    else:
        files = conn.get_files(
            study_id,
            version_id
        )
    files = [file_json_reformat(file, participants, devices, kinds, file_ids) for file in files]
    formatted_files = list([x for x in files if x is not None])
    return formatted_files

def get_file_content(file_id: str, stream: bool = True, decode: str = None):
    max_tries = 10  # Set the maximum number of retry attempts
    retry_delay = 10  # Set the delay in seconds between retries
    tries = 0
    
    while tries < max_tries:
        conn = DMPConnectiontRPC()
        try:
            # Attempt to get the file content
            content = conn.get_file(file_id, stream=stream)
            
            # Check if content is bytes when it should be
            if stream and not isinstance(content, bytes):
                raise TypeError(f"Expected bytes but got {type(content)}")
            
            # Handle decoding if requested
            if decode:
                try:
                    decoded_content = content.decode(decode)
                    return decoded_content
                except AttributeError:
                    raise TypeError(f"Cannot decode content of type {type(content)}")
            
            return content
        
        except (TypeError, AttributeError, Exception) as e:
            # Print the actual error message
            if 'Invalid URL' in str(e):
                time.sleep(retry_delay)
                continue
            if 'Please log in again' in str(e):
                time.sleep(retry_delay)
                continue
            if 'File is not a' in str(e):
                time.sleep(2 * retry_delay)
                tries += 1
                continue
            
            tries += 1
            if tries >= max_tries:
                print(f"Maximum attempts ({max_tries}) exceeded")
                return None
            
def archive_preview(file_id: str, file_name: str, verbose: bool = False):
    max_tries = 10
    retry_delay = 2

    tries = 0

    while tries < max_tries:
        try:
            # Your original block of code
            file_type = get_file_type(file_name)
            file_stream = get_file_content(file_id)
            compressed_data = BytesIO(file_stream)

            # If all lines succeed, break out of the retry loop
            break
        except Exception as e:
            # Increment tries and add delay if an error occurs
            tries += 1
            if tries >= max_tries:
                print(f"Error after {max_tries} attempts: {str(e)}")
            else:
                time.sleep(retry_delay)

    if not file_type or file_type not in ["zip", "tar.gz", "rar", "7z"]:
        print("Not an archive")
        return "Not an archive"
    else:
        if file_type == 'zip':
            with zipfile.ZipFile(compressed_data) as zf:
                verbose and print("ZIP file structure:")
                for file_info in zf.infolist():
                    verbose and print(file_info.filename)
                return [file_info.filename for file_info in zf.infolist()]
        elif file_type == 'tar.gz':
            with tarfile.open(fileobj=compressed_data, mode='r:gz') as tar:
                verbose and print("Tarred GZ file structure:")
                for tar_info in tar:
                    verbose and print(tar_info.name)
                return [tar_info.filename for tar_info in tar]
        elif file_type == 'rar':
            with rarfile.RarFile(compressed_data) as rf:
                verbose and print("RAR file structure:")
                for rar_info in rf.infolist():
                    verbose and print(rar_info.filename)
                return [rar_info.filename for rar_info in rf.infolist()]
        elif file_type == '7z':
            with py7zr.SevenZipFile(compressed_data, mode='r') as z:
                verbose and print("7Z file structure:")
                for name in z.getnames():
                    verbose and print(name)
                return [name for name in z.getnames()]


def stream_text_from_archive(file_id, file_name):
    return stream_data_from_archive(file_id, file_name, data_type='text')


def stream_data_from_archive(file_id, file_name, data_type='text'):
    max_tries = 3
    retry_delay = 2

    tries = 0

    while tries < max_tries:
        try:
            # Your original block of code
            file_type = get_file_type(file_name)
            file_stream = get_file_content(file_id)
            compressed_data = BytesIO(file_stream)

            # If all lines succeed, break out of the retry loop
            break
        except Exception as e:
            # Increment tries and add delay if an error occurs
            tries += 1
            if tries >= max_tries:
                print(f"Error after {max_tries} attempts: {str(e)}")
            else:
                time.sleep(retry_delay)
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
    max_tries = 3
    retry_delay = 2

    tries = 0

    while tries < max_tries:
        try:
            # Your original block of code
            file_type = get_file_type(file_name)
            file_stream = get_file_content(file_id)
            compressed_data = BytesIO(file_stream)

            # If all lines succeed, break out of the retry loop
            break
        except Exception as e:
            # Increment tries and add delay if an error occurs
            tries += 1
            if tries >= max_tries:
                print(f"Error after {max_tries} attempts: {str(e)}")
            else:
                time.sleep(retry_delay)

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

def get_study_fields(study_id: str, versionId=None):
    conn = DMPConnectiontRPC()
    fields = conn.get_study_fields(study_id, versionId)
    return [field_json_reformat(field) for field in fields]

def create_new_field(study_id: str, field_id: str, field_name: str, data_type: str, possible_values: Optional[Any] = None,
                     unit: Optional[str] = None, comments: Optional[str] = None, table_name: Optional[str] = None, properties = None):
    conn = DMPConnectiontRPC()
    new_data_type = 'str'
    if data_type == 'int':
        new_data_type = 'INTEGER'
    elif data_type == 'dec':
        new_data_type = 'DECIMAL'
    elif data_type == 'str':
        new_data_type = 'STRING'
    elif data_type == 'bool':
        new_data_type = 'BOOLEAN'
    elif data_type == 'date':
        new_data_type = 'DATETIME'
    elif data_type == 'file':
        new_data_type = 'FILE'
    elif data_type == 'json':
        new_data_type = 'JSON'
    elif data_type == 'cat':
        new_data_type = 'CATEGORICAL'
    else:
        new_data_type = 'STRING'
    field = conn.create_study_field(
        study_id=study_id,
        field_name=field_name,
        field_id=field_id,
        data_type=new_data_type,
        categorical_options=possible_values,
        unit=unit,
        comments=comments,
        metadata={"table": table_name},
        properties=properties
    )
    return field_json_reformat(field)

def upload_data(study_id: str, file_name: str, file_content: bytes, participant_id=None, device_id=None,
            start_date=None, end_date=None, field_id=None, properties = None):
    conn = DMPConnectiontRPC()
    field_id = get_field_id_from_device_id(device_id[:3]) if field_id is None else field_id
    if not field_id:
        print(f"Field not found for device {device_id}")
        return

    if properties is None:
        if not participant_id or not device_id or not start_date or not end_date:
            print(f"Missing properties for file {file_name}")
            return
        
    def ensure_milliseconds(ts: str) -> str:
        """
        Convert various date/timestamp formats to YYYY-MM-DD format.
        
        Args:
            ts: Input timestamp/date that could be:
                - Unix timestamp in seconds or milliseconds
                - String date in format YYYYMMDD
                - String date in format YYYY-MM-DD
                
        Returns:
            str: Date in YYYY-MM-DD format, or original string if conversion fails
        """
        if not ts:
            return ts
            
        # Try parsing as YYYY-MM-DD first
        try:
            datetime.strptime(ts, '%Y-%m-%d')
            return ts
        except (ValueError, TypeError):
            pass

        # Try parsing as YYYYMMDD
        try:
            if isinstance(ts, str) and len(ts) == 8 and ts.isdigit():
                return f"{ts[:4]}-{ts[4:6]}-{ts[6:]}"
        except (ValueError, TypeError):
            pass

        # Try parsing as timestamp (seconds or milliseconds)
        try:
            ts_int = int(float(ts))
            # If timestamp is in seconds (less than year 2100), convert to milliseconds
            if ts_int < 4102444800:  # 2100-01-01 in seconds
                ts_int *= 1000
            
            # Convert to UTC datetime and format as YYYY-MM-DD
            utc_dt = datetime.fromtimestamp(ts_int / 1000, tz=timezone.utc)
            return utc_dt.strftime('%Y-%m-%d')
            
        except (ValueError, TypeError):
            return ts  # Return original if conversion fails

    return conn.upload_study_file_data(
        study_id=study_id,
        field_id=field_id,
        properties=json.dumps({
            "FileName": file_name,
            "subjectId": participant_id,
            "deviceId": device_id,
            "startDate": ensure_milliseconds(start_date),
            "endDate": ensure_milliseconds(end_date)
        }) if properties is None else json.dumps(properties),
        file_name=file_name,
        file_content=file_content
    )

def get_data_records(study_id, field_ids, version_id='-1', data_format=None, table_requested=None, simple_grouping=False):
    conn = DMPConnectiontRPC()
    if version_id is None:
        data = conn.get_study_data(study_id, field_ids, None)
    elif version_id:
        if version_id == '-1':
            data = conn.get_study_data(study_id, field_ids, version_id)
        else:
            data = conn.get_study_data(study_id, field_ids, version_id)
    else:
        data = conn.get_data_latest(study_id, field_ids)
    subjects_to_remove = [
        'KZKCXRY', 'KHSAKES', 'KZYYPDC'
    ] + [
    'RQRPXCH', 'DTXZNTP', 'NJHRNPG', 'QJEGAQE', 'NEJRZKJ', 'RKSDXNQ', 'BYVSVYE',
    'KNEJYAA', 'KZYYPDC', 'KHSAKES', 'KZKCXRY', 'KHSAKES', 'KZYYPDC', 'KYYYYYY']

    filtered_data = [
        t for t in data if t.get('properties', {}).get('subjectId', None) not in subjects_to_remove
    ]
    if not simple_grouping:
        grouped = {}
        for record in filtered_data:
            try:
                subject_id = record.get('properties', {}).get('subjectId', None)
                visit_id = record.get('properties', {}).get('visitId', None)
                field_id = record.get('fieldId', None)
                value = record.get('value', None)
                if not subject_id or not visit_id:
                    print(f"Record {record['id']} does not have subjectId or visitId")
                    continue
                if subject_id not in grouped:
                    grouped[subject_id] = {}
                if visit_id not in grouped[subject_id]:
                    grouped[subject_id][visit_id] = {}
                grouped[subject_id][visit_id][field_id] = value
            except:
                print('error', record)
                break
        return grouped
    if simple_grouping:
        grouped = {}
        for record in filtered_data:
            try:
                field_id = record.get('fieldId', None)
                if field_id not in grouped:
                    grouped[field_id] = []
                grouped[field_id].append(record)
            except:
                print('error', record)
                break
        return grouped
    

def upload_data_in_array(study_id, data):
    conn = DMPConnectiontRPC()
    res = conn.upload_study_data(study_id, convert_v2_data_clip_input_to_v3(data))
    return {
        'data': {
            'uploadDataInArray': res
        }
    }

def fetch_adam_data(study_id, domain, version_id=None):
        """
            Python wrapper for data.fetchAdamData.
        """
        conn = DMPConnectiontRPC()

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
            "derived_SubjectgroupCharacterisation_timesincediagnosis", "derived_TUP1_start_date", "derived_TUP2_start_date","derived_TUP3_start_date","derived_TUP4_start_date","derived_TUP1_stop_date","derived_TUP2_stop_date","derived_TUP3_stop_date","derived_TUP4_stop_date", "derived_Demographics_DateofAssessment", "ias_train_test",
            "derived_TUPstudy_start_start_date"
        ]


        if domain == 'ADSL':
            return adsl(conn, study_id, derived_fields, version_id)
        elif domain == 'ADPRO':
            adsl_data = adsl(conn, study_id, derived_fields, version_id)
            adpro_data = adpro(conn, study_id, derived_fields, version_id)
            adpro_data = flag_invalid_pro_dates(adsl_data, adpro_data, acceptable_delay=3)
            return adpro_data
        elif domain == 'ADDI':
            return addi(conn, study_id, derived_fields, version_id)
        elif domain == 'ADCL':
            return adcl(conn, study_id, derived_fields, version_id)
        else:
            print(f"Domain {domain} not recognized.")
            return None

def adsl(conn, study_id, derived_fields, version_id='-1'):
    desired_order = ['USUBJID','SITE','REGION','COUNTRY','STUDYID','COHORT','DEMOCOLLDTC','ANALYSISSET','IASSET','BMI','HEIGHT','WEIGHT','AGE','AGEU','AGECAT','GENDER','OCCUPATION','EDUCATION','ETHNICITY','TIMESINCEDIAG','TUPSTDT','TUP1DT','TUP1DE','TUP1TZ','TUP2DT','TUP2DE','TUP2TZ','TUP3DT','TUP3DE','TUP3TZ','TUP4DT','TUP4DE','TUP4TZ']
    adsl_raw_data = get_data_records(
        study_id=study_id,
        field_ids=derived_fields,
        version_id=version_id
    )

    study = conn.get_studies(study_id)[0]

    data = {}
    # 1167
    site_mapping = {
        '1': 'Kiel',
        '2': 'Muenseter (GHI)',
        '3': 'Rotterdam (Erasmus)',
        '4': 'Harrow',
        '5': 'Leeds (Yorkshire)',
        '6': 'Devon & Exeter',
        '7': 'Pennine Acute Hospitals (in Manchester - Odham, Rochdale, Fairfield)',
        '8': 'Glasgow (along the river Clyde)',
        '9': 'Manchester',
        '10': 'QMUL',
        '11': 'Cork University Hospital',
        '12': 'Newcastle',
        '13': 'Leiden',
        '14': 'Brescia',
        '15': 'Lisbon (Portugal)',
        '16': 'Innsbruck (Austria)',
        '17': 'Warshaw',
        '18': 'Madrid (Spain)',
        '19': 'Stavanger (Rogaland, Norway)',
        '20': 'Addenbrookes - Cambridge'
    }
    # derived_Demographics_Region
    region_mapping = {
        '0': 'EC',
        '1': "SC",
        '2': 'WC'
    }
    # derived_Demographics_Country
    country_mapping = {
        '0': 'AT',
        '1': 'DE',
        '2': 'ES',
        '3': 'IE',
        '4': 'IT',
        '5': 'NL',
        '6': 'NO',
        '7': 'PL',
        '8': 'PT',
        '9': 'UK'
    }
    # 1168
    cohort_mapping = {
        '0': 'HV',
        '1': 'HD',
        '2': 'IBD',
        '3': 'PD',
        '4': 'PSS',
        '5': 'RA',
        '6': 'SLE'
    }
    # dataset_id
    dataset_mapping = {
        '1': 'ISA',
        '2': 'ESA'
    }
    # derived_Demographics_AgeCat
    age_cat_mapping = {
        '0': '(18, 42]',
        '1': '(42, 120]',
        '2': '(42, 120]',
        '3': '(48.5, 120]',
        '4': '(18, 36.5]',
        '5': '(36.5, 120]',
        '6': '(18, 63.5]',
        '7': '(63.5, 120]',
        '8': '(18, 66.5]',
        '9': '(66.5, 120]',
        '10': '(18, 66]',
        '11': '(66, 120]',
        '12': '(18, 49.5]',
        '13': '(49.5, 120]'
    }
    # 1148
    gender_mapping = {
        '0': 'Male',
        '1': 'Female',
        '2': 'NA'
    }
    # 1146
    occupation_mapping = {
        '0': 'Retired',
        '1': 'Not working (unable to work)',
        '2': '1 part-time job',
        '3': '2-3 part-time jobs',
        '4': '4 or more part-time jobs',
        '5': 'Full time',
        '6': 'Full time carer',
        '7': 'Housewife/Househusband'
    }
    # 1141
    education_mapping = {
        '0': 'Primary or no formal education',
        '1': 'Secondary',
        '2': 'Professional certificates or diploma (below degree levels)',
        '3': 'University undergraduate degrees',
        '4': 'Postgraduate degrees or higher'
    }
    # 1143
    ethnicity_mapping = {
        '0': 'Black',
        '1': 'White',
        '2': 'Chinese',
        '3': 'Hispanic',
        '4': 'Asian',
        '5': 'Mixed',
        '6': 'From Colombia, indigenous ancestry',
        '7': 'Prefer not to say / disclose'
    }
    # ias mapping 
    ias_mapping = {
        '1': 'Train',
        '2': 'Test'
    }

    for subject_id in adsl_raw_data:
        for visit_id in adsl_raw_data[subject_id]:
            for field_id in adsl_raw_data[subject_id][visit_id]:
                if subject_id not in data:
                    data[subject_id] = {}
                    data[subject_id]['USUBJID'] = subject_id
                    data[subject_id]['STUDYID'] = study.get('name', None)

                if field_id == '1167':
                    data[subject_id]['SITE'] = site_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == 'derived_Demographics_Region':
                    data[subject_id]['REGION'] = region_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == 'derived_Demographics_Country':
                    data[subject_id]['COUNTRY'] = country_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == '1168':
                    data[subject_id]['COHORT'] = cohort_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == 'derived_Demographics_DateofAssessment':
                    data[subject_id]['DEMOCOLLDTC'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'dataset_id':
                    data[subject_id]['ANALYSISSET'] = dataset_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == 'derived_Demographics_BMI':
                    data[subject_id]['BMI'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == '1145':
                    data[subject_id]['HEIGHT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == '1151':
                    data[subject_id]['WEIGHT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_Demographics_Age':
                    data[subject_id]['AGE'] = adsl_raw_data[subject_id][visit_id][field_id]
                    data[subject_id]['AGEU'] = 'YEARS'
                    continue
                if field_id == 'derived_Demographics_AgeCat':
                    data[subject_id]['AGECAT'] = age_cat_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == '1148':
                    data[subject_id]['GENDER'] = gender_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == '1146':
                    data[subject_id]['OCCUPATION'] = occupation_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == '1141':
                    data[subject_id]['EDUCATION'] = education_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == '1143':
                    data[subject_id]['ETHINICITY'] = ethnicity_mapping.get(adsl_raw_data[subject_id][visit_id][field_id], None)
                    continue
                if field_id == 'derived_SubjectgroupCharacterisation_timesincediagnosis':
                    data[subject_id]['TIMESINCEDIAG'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUPstudy_start_start_date':
                    data[subject_id]['TUPSTDT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP1_start_date':
                    data[subject_id]['TUP1DT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP1_stop_date':
                    data[subject_id]['TUP1DE'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP1_start_timezone':
                    data[subject_id]['TUP1TZ'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP2_start_date':
                    data[subject_id]['TUP2DT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP2_stop_date':
                    data[subject_id]['TUP2DE'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP2_start_timezone':
                    data[subject_id]['TUP2TZ'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP3_start_date':
                    data[subject_id]['TUP3DT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP3_stop_date':
                    data[subject_id]['TUP3DE'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP3_start_timezone':
                    data[subject_id]['TUP3TZ'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP4_start_date':
                    data[subject_id]['TUP4DT'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP4_stop_date':
                    data[subject_id]['TUP4DE'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'derived_TUP4_start_timezone':
                    data[subject_id]['TUP4TZ'] = adsl_raw_data[subject_id][visit_id][field_id]
                    continue
                if field_id == 'ias_train_test':
                    data[subject_id]['IASSET'] = ias_mapping.get(adsl_raw_data[subject_id][visit_id][field_id],
                    None)
                    continue

    for subject in data:
        for key in desired_order:
            if key not in data[subject]:
                data[subject][key] = ''
    df_array = []
    for subject in data:
        df_array.append(data[subject])
    df = pd.DataFrame(df_array)
    df['DEMOCOLLDTC'] = df['DEMOCOLLDTC'].apply(convert_to_date)
    df['TUPSTDT'] = df['TUPSTDT'].apply(convert_to_date)
    df['TUP1DT'] = df['TUP1DT'].apply(convert_to_date)
    df['TUP1DE'] = df['TUP1DE'].apply(convert_to_date)
    df['TUP2DT'] = df['TUP2DT'].apply(convert_to_date)
    df['TUP2DE'] = df['TUP2DE'].apply(convert_to_date)
    df['TUP3DT'] = df['TUP3DT'].apply(convert_to_date)
    df['TUP3DE'] = df['TUP3DE'].apply(convert_to_date)
    df['TUP4DT'] = df['TUP4DT'].apply(convert_to_date)
    df['TUP4DE'] = df['TUP4DE'].apply(convert_to_date)


    return df[desired_order]

def flag_invalid_pro_dates(participants: pd.DataFrame, pros: pd.DataFrame, acceptable_delay: int=3):
    """
    Flag PROs for which date of completion is too far from the expected date (TUP start or end date).

    Parameters
    ----------
    participants: pd.DataFrame
        input dataframe with ADSL data
    pros: pd.DataFrame
        input dataframe with ADPRO data
    acceptable_delay: int
        number of acceptable delay between PRO date and TUP date (in days)

    Returns
    -------
    pros dataframe with a new colum "FLAG"

    """
    data = pros.copy()
    
    tup_dates = participants[[
        "USUBJID", "TUP1DT", "TUP1DE", "TUP2DT", "TUP2DE", "TUP3DT", "TUP3DE", "TUP4DT", "TUP4DE"
    ]].melt(id_vars="USUBJID", var_name="TUP", value_name="TUPDT")
    tup_dates.replace("", np.nan, inplace=True)
    tup_dates.dropna(inplace=True)

    tup_dates["VISITNUM"] = tup_dates.TUP.map({
        "TUP1DT": "Visit 1",
        "TUP1DE": "Visit 2",
        "TUP2DT": "Visit 3",
        "TUP2DE": "Visit 4",
        "TUP3DT": "Visit 5",
        "TUP3DE": "Visit 6",
        "TUP4DT": "Visit 7",
        "TUP4DE": "Visit 8",    
    })

    data = data.merge(tup_dates[["USUBJID", "VISITNUM", "TUPDT"]], how="left") 
    data["delay"] = (pd.to_datetime(data.TUPDT) - pd.to_datetime(data.ADT)).dt.days

    data["FLAG"] = "valid"
    data.loc[data.delay.abs() > acceptable_delay, "FLAG"] = "invalid"

    pros = pros.merge(data[["USUBJID", "VISITNUM", "FORMID", "PARAMCD", "FLAG"]], how="outer")
    return(pros)


def process_subject_data(subject_id, adpro_raw_data, study, atup_mapping, kss_mapping, pgi_1241_mapping, pgi_1242_mapping, pgi_1249_mapping, pgi_1250_mapping, pgi_1235_mapping, pgi_1236_mapping, format1, format2):
    desired_order = ['USUBJID', 'STUDYID', 'ANALYSISSET', 'IASSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'ADY', 'AVAL', 'AVALC', 'FORMID', 'FORMNAME', 'PARAM', 'PARAMCD']
    data = {}
    dataset_mapping = {
        '1': 'ISA',
        '2': 'ESA'
    }
    ias_mapping = {
        '1': 'Train',
        '2': 'Test'
    }

    # Process data for the given subject_id
    for visit_id in adpro_raw_data[subject_id]:
        for field_id in adpro_raw_data[subject_id][visit_id]:
            if subject_id not in data:
                data[subject_id] = {}
            if visit_id not in data[subject_id]:
                data[subject_id][visit_id] = {}
            if field_id not in data[subject_id][visit_id]:
                data[subject_id][visit_id][field_id] = []
            
            dataclip = {}
            dataclip['USUBJID'] = subject_id
            dataclip['STUDYID'] = study.get('name', None)
            dataclip['ANALYSISSET'] = dataset_mapping.get(adpro_raw_data[subject_id][visit_id].get('dataset_id', None), None)
            dataclip['IASSET'] = ias_mapping.get(adpro_raw_data[subject_id][visit_id].get('ias_train_test', None), None)
            dataclip['VISITNUM'] = 'Visit ' + visit_id
            dataclip['AVISIT'] = 'Visit ' + visit_id
            dataclip['TUPNUM'] = 'TUP ' + str(math.ceil(int(visit_id) / 2))
            dataclip['ATUP'] = atup_mapping.get(visit_id, None)

            if field_id == 'derived_FACITF_score':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_FACITF_DateofAssessment', None)
                dataclip['FORMID'] = 'FACIT-F'
                dataclip['FORMNAME'] = 'Functional Assessment of Chronic Illness Therapy - Fatigue'
                dataclip['PARAM'] = 'FACIT-F Score'
                dataclip['PARAMCD'] = 'FACITF-SCORE'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_fVAS_fvas':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_fVAS_DateofAssessment', None)
                dataclip['FORMID'] = 'fVAS'
                dataclip['FORMNAME'] = 'Fatigue Visual Analogue Scale'
                dataclip['PARAM'] = 'How fatigues did you feel overall withun the last 7 days'
                dataclip['PARAMCD'] = 'fVAS'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_mMFS_score':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_mMFS_DateofAssessment', None)
                dataclip['FORMID'] = 'mMFS'
                dataclip['FORMNAME'] = 'Modified Fatigue Severity Scale'
                dataclip['PARAM'] = 'mMFS toal Score'
                dataclip['PARAMCD'] = 'mMFS-SCORE'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == '695':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_KSS_DateofAssessment', None)
                dataclip['FORMID'] = 'KSS'
                dataclip['FORMNAME'] = 'Karolinska Sleepiness Scale'
                dataclip['PARAM'] = 'How did you feel on average during the last 7 days'
                dataclip['PARAMCD'] = 'KSS'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = kss_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            elif field_id == 'derived_ESS_score':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_ESS_DateofAssessment', None)
                dataclip['FORMID'] = 'ESS'
                dataclip['FORMNAME'] = 'Epworth Sleepiness Scale'
                dataclip['PARAM'] = 'ESS total score'
                dataclip['PARAMCD'] = 'ESS-SCORE'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_sqVAS_sqvas':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_sqVAS_DateofAssessment', None)
                dataclip['FORMID'] = 'sqVAS'
                dataclip['FORMNAME'] = 'Sleep Quality Visual Analogue Scale'
                dataclip['PARAM'] = 'How was your sleep within the last 7 days'
                dataclip['PARAMCD'] = 'sqVAS'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPD4':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale Sleep disturbance'
                dataclip['PARAMCD'] = 'SLPD4'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPSNR1':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale Snoring'
                dataclip['PARAMCD'] = 'SLPSNR1'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPSOB1':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale sleep short of breath or headache'
                dataclip['PARAMCD'] = 'SLPSOB1'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPA2':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale sleep adequacy'
                dataclip['PARAMCD'] = 'SLPA2'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPS3':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale sleep quantity'
                dataclip['PARAMCD'] = 'SLPS3'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLP6':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale Sleep problems index I'
                dataclip['PARAMCD'] = 'SLP6'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLP9':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale Sleep problems index II'
                dataclip['PARAMCD'] = 'SLP9'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPQRAW':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale sleep quantity'
                dataclip['PARAMCD'] = 'SLPQRAW'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == 'derived_MOSSS_SLPOP1':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_MOSSS_DateofAssessment', None)
                dataclip['FORMID'] = 'aMOS-SS'
                dataclip['FORMNAME'] = 'Medical Outcomes Study Sleep Scale acute questionnaire'
                dataclip['PARAM'] = 'aMOS-SS subscale optimal sleep'
                dataclip['PARAMCD'] = 'SLPOP1'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = adpro_raw_data[subject_id][visit_id][field_id]
            elif field_id == '1241':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_PGIF_DateofAssessment', None)
                dataclip['FORMID'] = 'PGI-F'
                dataclip['FORMNAME'] = 'Patient Global Impression Fatigue'
                dataclip['PARAM'] = 'Compared to the last technology use period (about 2 months before) my fatigue is (1: Very much improved; 2: Much Improved; 3: Minimally Improved; 4: No Change; 5: Minimally Worse; 6: Much Worse; 7: Very Much Worse)'
                dataclip['PARAMCD'] = 'PGIC-F'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = pgi_1241_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            elif field_id == '1242':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_PGIF_DateofAssessment', None)
                dataclip['FORMID'] = 'PGI-F'
                dataclip['FORMNAME'] = 'Patient Global Impression Fatigue'
                dataclip['PARAM'] = 'Check the one box that describes how your fatigue is now (1: No Fatigue; 2: Mild Fatigue; 3: Moderate Fatigue; 4: Severe Fatigue)'
                dataclip['PARAMCD'] = 'PGIS-F'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = pgi_1242_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            elif field_id == '1249':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_PGISQ_DateofAssessment', None)
                dataclip['FORMID'] = 'PGI-SQ'
                dataclip['FORMNAME'] = 'Patient Global Impression Sleep Quality'
                dataclip['PARAM'] = 'Compared to the last technology use period (about 2 months before) my sleep quality is (1: Very much improved; 2: Much Improved; 3: Minimally Improved; 4: No Change; 5: Minimally Worse; 6: Much Worse; 7: Very Much Worse)'
                dataclip['PARAMCD'] = 'PGIC-SQ'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = pgi_1249_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            elif field_id == '1250':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_PGISQ_DateofAssessment', None)
                dataclip['FORMID'] = 'PGI-SQ'
                dataclip['FORMNAME'] = 'Patient Global Impression Disease Severity'
                dataclip['PARAM'] = 'Check the one box that describes how your sleep quality is now (1: No Fatigue; 2: Mild Fatigue; 3: Moderate Fatigue; 4: Severe Fatigue)'
                dataclip['PARAMCD'] = 'PGIS-SQ'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = pgi_1250_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            elif field_id == '1235':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_PGIDS_DateofAssessment', None)
                dataclip['FORMID'] = 'PGI-DS'
                dataclip['FORMNAME'] = 'Patient Global Impression Daytime Sleepiness'
                dataclip['PARAM'] = 'Compared to the last technology use period (about 2 months before) my daytime sleepiness is (1: Very much improved; 2: Much Improved; 3: Minimally Improved; 4: No Change; 5: Minimally Worse; 6: Much Worse; 7: Very Much Worse)'
                dataclip['PARAMCD'] = 'PGIC-DS'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = pgi_1235_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            elif field_id == '1236':
                dataclip['ADT'] = adpro_raw_data[subject_id][visit_id].get('derived_PGIDS_DateofAssessment', None)
                dataclip['FORMID'] = 'PGI-DS'
                dataclip['FORMNAME'] = 'Patient Global Impression Daytime Sleepiness'
                dataclip['PARAM'] = 'Check the one box that describes how your daytime sleepiness is now (1: No Fatigue; 2: Mild Fatigue; 3: Moderate Fatigue; 4: Severe Fatigue)'
                dataclip['PARAMCD'] = 'PGIS-DS'
                dataclip['AVAL'] = adpro_raw_data[subject_id][visit_id][field_id]
                dataclip['AVALC'] = pgi_1236_mapping.get(adpro_raw_data[subject_id][visit_id][field_id], None)
            else:
                continue
            # Calculate ADT (this part involves some complex logic with date/time)
            ADT = dataclip.get('ADT', None)
            if subject_id and visit_id and ADT:
                tup_key = 'derived_TUP' + str(int(math.ceil(int(visit_id)/2))) + '_start_date'
                result = 'NA'
                if tup_key in adpro_raw_data[subject_id]['0']:
                    time1_dt = datetime.strptime(ADT, format1)
                    time2_dt = datetime.strptime(adpro_raw_data[subject_id]['0'][tup_key], format2)
                    difference = time1_dt - time2_dt
                    result = str(difference)
                dataclip['ADY'] = result
            else:
                dataclip['ADY'] = ''
            dataclip['ADT'] = convert_to_date_single(dataclip['ADT'])
            for key in desired_order:
                if key not in dataclip:
                    dataclip[key] = ''
            
            data[subject_id][visit_id][field_id].append(dataclip)

    # Collect data into a list of dictionaries
    df_array = []
    for visit_id in data[subject_id]:
        for field_id in data[subject_id][visit_id]:
            df_array.extend(data[subject_id][visit_id][field_id])
    
    return df_array

def adpro(conn, study_id, derived_fields, version_id='-1'):
    desired_order = ['USUBJID', 'STUDYID', 'ANALYSISSET', 'IASSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'ADY', 'AVAL', 'AVALC', 'FORMID', 'FORMNAME', 'PARAM', 'PARAMCD']
    format1 = "%Y-%m-%dT%H:%M:%S.%f"
    format2 = "%Y-%m-%d %H:%M:%S"

    # Get raw data from your source
    adpro_raw_data = get_data_records(study_id=study_id, field_ids=derived_fields,
        version_id=version_id)
    study = conn.get_studies(study_id)[0]
    
    # Mapping dictionaries (same as your original code)
    atup_mapping = {
        '1': 'Start of TUP 1',
        '2': 'End of TUP 1',
        '3': 'Start of TUP 2',
        '4': 'End of TUP 2',
        '5': 'Start of TUP 3',
        '6': 'End of TUP 3',
        '7': 'Start of TUP 4',
        '8': 'End of TUP 4'
    }
    # kss
    kss_mapping = {
        '1': 'extremely alert',
        '2': 'very alert',
        '3': 'alert',
        '4': 'rather alert',
        '5': 'neither alert nor sleepy',
        '6': 'some signs of sleepiness',
        '7': 'sleepy, but no effort to keep awake',
        '8': 'sleepy, but some effort to keep awake',
        '9': 'very sleepy, great effort to keep awake, fighting sleep',
        '10': 'extremely sleepy, can\'t keep awake'
    }
    # 1241
    pgi_1241_mapping = {
        '1': 'Very much improved',
        '2': 'Much improved',
        '3': 'Minimally improved',
        '4': 'No change',
        '5': 'Minimally worse',
        '6': 'Much worse',
        '7': 'Very much worse'
    }
    # 1242
    pgi_1242_mapping = {
        '1': 'No fatigue',
        '2': 'Mild fatigue',
        '3': 'Moderate fatigue',
        '4': 'Severe fatigue'
    }
    # 1249
    pgi_1249_mapping = {
        '1': 'Very much improved',
        '2': 'Much improved',
        '3': 'Minimally improved',
        '4': 'No change',
        '5': 'Minimally worse',
        '6': 'Much worse',
        '7': 'Very much worse'
    }
    # 1250
    pgi_1250_mapping = {
        '1': 'Normal',
        '2': 'Mild sleep disturbances',
        '3': 'Moderate sleep disturbances',
        '4': 'Severe sleep disturbances'
    }
    # 1235
    pgi_1235_mapping = {
        '1': 'Very much improved',
        '2': 'Much improved',
        '3': 'Minimally improved',
        '4': 'No change',
        '5': 'Minimally worse',
        '6': 'Much worse',
        '7': 'Very much worse'
    }
    # 1236
    pgi_1236_mapping = {
        '1': 'No daytime sleepiness',
        '2': 'Mild daytime sleepiness',
        '3': 'Moderate daytime sleepiness',
        '4': 'Severe daytime sleepiness'
    }

    # dataset_id
    dataset_mapping = {
        '1': 'ISA',
        '2': 'ESA'
    }
    ias_mapping = {
        '1': 'Train',
        '2': 'Test'
    }

    # Use partial to set up the function with pre-filled arguments
    process_partial = partial(
        process_subject_data,
        adpro_raw_data=adpro_raw_data,
        study=study,
        atup_mapping=atup_mapping,
        kss_mapping=kss_mapping,
        pgi_1241_mapping=pgi_1241_mapping,
        pgi_1242_mapping=pgi_1242_mapping,
        pgi_1249_mapping=pgi_1249_mapping,
        pgi_1250_mapping=pgi_1250_mapping,
        pgi_1235_mapping=pgi_1235_mapping,
        pgi_1236_mapping=pgi_1236_mapping,
        format1=format1,
        format2=format2
    )

    # Use multiprocessing to process data for each subject in parallel
    with mp.Pool(8) as pool:
        results = pool.map(process_partial, adpro_raw_data.keys())

    # Combine all the results
    df_array = [item for sublist in results for item in sublist]

    # Create the final DataFrame
    df = pd.DataFrame(df_array)

    return df[desired_order]

def addi(conn, study_id, derived_fields, version_id='-1'):
    addi_data = get_data_records(
        study_id=study_id,
        field_ids=["derived_ADDI"],
        version_id=version_id
    )
    dataset_id_data = get_data_records(
        study_id=study_id,
        field_ids=['dataset_id'],
        version_id=version_id
    )
    ias_data = get_data_records(
        study_id=study_id,
        field_ids=['ias_train_test'],
        version_id=version_id
    )
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
    dataframe = []
    desired_order = ['USUBJID', 'STUDYID', 'ANALYSISSET', 'IASSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'ATM', 'TIMING', 'AVAL', 'AVALC', 'PARAM', 'PARAMCD']
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
            if ias_data.get(subjectId, {}).get(visitId):
                if ias_data[subjectId][visitId]['ias_train_test'] == '1':
                    tmp.append('TRAIN')
                elif ias_data[subjectId][visitId]['ias_train_test'] == '2':
                    tmp.append('TEST')
                else:
                    tmp.append('')
            else:
                tmp.append('')
            tmp.append(str(visitId))
            tmp.append('Visit ' + str(visitId))
            tmp.append('TUP ' + str(math.ceil(int(visitId) / 2)))
            tmp.append(ATUP_mapping[str(visitId)])
            # print(addi_data[subjectId][visitId]['derived_ADDI'])
            # First, load the outer JSON string
            data_string = json.loads(addi_data[subjectId][visitId]['derived_ADDI'])
            # Replace single quotes with double quotes in the inner JSON string
            data_string = data_string.replace("'", '"')
            # Now parse the inner JSON string
            data_clip = json.loads(data_string)
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
    df = pd.DataFrame(dataframe[1:], columns=dataframe[0])
    return df    

def adcl(conn, study_id, derived_fields, version_id='-1'):
    desired_order = ['USUBJID','STUDYID','ANALYSISSET', 'IASSET', 'VISITNUM', 'AVISIT', 'TUPNUM', 'ATUP', 'ADT', 'AVAL', 'AVALC', 'FORMID', 'FORMNAME', 'PARAM', 'PARAMCD']
    adcl_data = get_data_records(
        study_id=study_id,
        field_ids=derived_fields,
        version_id=version_id
    )
    study_name = conn.get_studies(study_id)[0].get('name', None)
    data = {}

    dataset_mapping = {
        '1': 'ISA',
        '2': 'ESA'
    }
    ias_mapping = {
        '1': 'Train',
        '2': 'Test'
    }
    
    for subject_id in adcl_data:
        for visit_id in adcl_data[subject_id]:
            for field_id in adcl_data[subject_id][visit_id]:
                if subject_id not in data:
                    data[subject_id] = {}
                if visit_id not in data[subject_id]:
                    data[subject_id][visit_id] = {}
                if field_id not in data[subject_id][visit_id]:
                    data[subject_id][visit_id][field_id] = []
                dataclip = {}
                dataclip['USUBJID'] = subject_id
                dataclip['STUDYID'] = study_name
                dataclip['ANALYSISSET'] = dataset_mapping.get(adcl_data[subject_id][visit_id].get('dataset_id', None), None)
                dataclip['IASSET'] = ias_mapping.get(adcl_data[subject_id][visit_id].get('ias_train_test', None), None)
                dataclip['VISITNUM'] = 'Visit ' + visit_id
                dataclip['AVISIT'] = 'Visit ' + visit_id
                dataclip['TUPNUM'] = 'TUP ' + str(math.ceil(int(visit_id) / 2))
                dataclip['ATUP'] = 'NA'

                if field_id == 'derived_MDSUPDRSII_mdsupdrs2_score':
                    dataclip['FORMID'] = 'MDS-UPDRS'
                    dataclip['FORMNAME'] = 'revision of the Unified Parkinson\'s Disease Rating Scale'
                    dataclip['PARAM'] = 'MDS-UPDRS motor experiences of daily linving - total score'
                    dataclip['PARAMCD'] = 'MDSUPDRS2-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_MDSUPDRSII_disease_severity_cat_id':
                    dataclip['FORMID'] = 'MDS-UPDRS'
                    dataclip['FORMNAME'] = 'revision of the Unified Parkinson\'s Disease Rating Scale'
                    dataclip['PARAM'] = 'MDS-UPDRS motor experiences of daily linving - disease severity'
                    dataclip['PARAMCD'] = 'MDSUPDRS2-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Mild',
                        '2': 'Moderate',
                        '3': 'Severe'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                elif field_id == 'derived_MDSUPDRSIII_mdsupdrs3_score':
                    dataclip['FORMID'] = 'MDS-UPDRS'
                    dataclip['FORMNAME'] = 'revision of the Unified Parkinson\'s Disease Rating Scale'
                    dataclip['PARAM'] = 'MDS-UPDRS motor examination - total score'
                    dataclip['PARAMCD'] = 'MDSUPDRS3-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_MDSUPDRSIII_disease_severity_cat_id':
                    dataclip['FORMID'] = 'MDS-UPDRS'
                    dataclip['FORMNAME'] = 'revision of the Unified Parkinson\'s Disease Rating Scale'
                    dataclip['PARAM'] = 'MDS-UPDRS motor examination - disease severity'
                    dataclip['PARAMCD'] = 'MDSUPDRS3-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Mild',
                        '2': 'Moderate',
                        '3': 'Severe'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                elif field_id == 'derived_UHDRS_tfc_score':
                    dataclip['FORMID'] = 'UHDRS'
                    dataclip['FORMNAME'] = 'Unified Huntington\'s Disease Rating Scale'
                    dataclip['PARAM'] = 'UHDRS Total Functional Capacity - total score'
                    dataclip['PARAMCD'] = 'UHDRS-TFC-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_UHDRS_disease_severity_cat_id':
                    dataclip['FORMID'] = 'UHDRS'
                    dataclip['FORMNAME'] = 'Unified Huntington\'s Disease Rating Scale'
                    dataclip['PARAM'] = 'UHDRS Total Functional Capacity - disease severity'
                    dataclip['PARAMCD'] = 'UHDRS-TFC-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Mild',
                        '2': 'Moderate',
                        '3': 'Severe'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                elif field_id == 'derived_ESSDAI_ESSDAI_score':
                    dataclip['FORMID'] = 'ESSDAI'
                    dataclip['FORMNAME'] = 'EULAR Sjögren\'s syndrome Disease Activity Index'
                    dataclip['PARAM'] = 'ESSDAI total score'
                    dataclip['PARAMCD'] = 'ESSDAI-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_ESSDAI_disease_severity_cat_id':
                    dataclip['FORMID'] = 'ESSDAI'
                    dataclip['FORMNAME'] = 'EULAR Sjögren\'s syndrome Disease Activity Index'
                    dataclip['PARAM'] = 'ESSDAI disease severity'
                    dataclip['PARAMCD'] = 'ESSDAI-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Mild',
                        '2': 'Moderate',
                        '3': 'Severe'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                elif field_id == 'derived_SLEDAI2K_SLEDAI_score':
                    dataclip['FORMID'] = 'SLEDAI2K'
                    dataclip['FORMNAME'] = 'Systemic Lupus Erythematosus Disease Activity Index 2000'
                    dataclip['PARAM'] = 'SLEDAI2K total score'
                    dataclip['PARAMCD'] = 'SLEDAI2K-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_SLEDAI2K_disease_severity_cat_id':
                    dataclip['FORMID'] = 'SLEDAI2K'
                    dataclip['FORMNAME'] = 'Systemic Lupus Erythematosus Disease Activity Index 2000'
                    dataclip['PARAM'] = 'SLEDAI2K disease severity'
                    dataclip['PARAMCD'] = 'SLEDAI2K-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Mild',
                        '2': 'Moderate',
                        '3': 'Severe'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                elif field_id == 'derived_DiseaseActivityScore_DAS28_CRP':
                    dataclip['FORMID'] = 'DAS28'
                    dataclip['FORMNAME'] = 'Disease Activity Score 28 for Rhumatoid Arthrisis'
                    dataclip['PARAM'] = 'DAS28-CRP score'
                    dataclip['PARAMCD'] = 'DAS28-CRP-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_DiseaseActivityScore_disease_severity_cat_id':
                    dataclip['FORMID'] = 'DAS28'
                    dataclip['FORMNAME'] = 'Disease Activity Score 28 for Rhumatoid Arthrisis'
                    dataclip['PARAM'] = 'DAS28-CRP disease severity'
                    dataclip['PARAMCD'] = 'DAS28-CRP-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Remission',
                        '2': 'Mild',
                        '3': 'Moderate',
                        '4': 'Severe'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                elif field_id == 'derived_LabParameters_calprotectin':
                    dataclip['FORMID'] = 'Calprotectin'
                    dataclip['FORMNAME'] = 'Calprotectin'
                    dataclip['PARAM'] = 'Calprotectin'
                    dataclip['PARAMCD'] = 'Calprotectin-SCORE'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = adcl_data[subject_id][visit_id][field_id]
                elif field_id == 'derived_LabParameters_disease_severity_cat_id':
                    dataclip['FORMID'] = 'Calprotectin'
                    dataclip['FORMNAME'] = 'Calprotectin'
                    dataclip['PARAM'] = 'Calprotectin disease severity'
                    dataclip['PARAMCD'] = 'Calprotectin-DISEASECAT'
                    dataclip['AVAL'] = adcl_data[subject_id][visit_id][field_id]
                    dataclip['AVALC'] = {
                        '1': 'Inactive',
                        '2': 'Active'
                    }.get(adcl_data[subject_id][visit_id][field_id], None)
                else:
                    continue

                for key in desired_order:
                    if key not in dataclip:
                        dataclip[key] = ''
                data[subject_id][visit_id][field_id].append(dataclip)
    df_array = []
    for subject_id in data:
        for visit_id in data[subject_id]:
            for field_id in data[subject_id][visit_id]:
                df_array = df_array + data[subject_id][visit_id][field_id]
                
    df = pd.DataFrame(df_array)
    return df[desired_order]


def list_study_versions(study_id):
    conn = DMPConnectiontRPC()
    study = conn.get_studies(study_id)[0]

    versions = study['dataVersions']

    return pd.DataFrame([{
        'id': v['id'],
        'version': v['version'],
        'tag': v['tag'],
        'created': datetime.utcfromtimestamp(v['life']['createdTime'] / 1000).strftime('%Y-%m-%d')
    } for v in versions])



# used for DMP V3
