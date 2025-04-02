import json
from copy import deepcopy
from datetime import datetime, timezone
import pandas as pd


def read_json(file_path: str):
    try:
        with open(file_path) as f:
            return json.load(f)
    except:
        return 'Can not open ' + file_path 

def get_file_type(fname: str) -> str:
    base, extension = os.path.splitext(fname)
    if extension == ".gz" and base.endswith(".tar"):
        return "tar.gz"
    else:
        return extension.lstrip(".")

def file_json_reformat(file_json, participants=None, devices=None, kinds=None, file_ids=None):
        utt = file_json.get('life', {}).get('createdTime')
        if isinstance(utt, str):
            utt = int(utt)
        start_stamp = file_json.get('properties', {}).get("startDate", None)
        end_stamp = file_json.get('properties', {}).get("endDate", None)

        participant = file_json.get('properties', {}).get("subjectId", None)
        if participants is not None and participant not in participants:
            return None
        device_id = file_json.get('properties').get("deviceId", None)
        if devices is not None and device_id not in devices:
            return None
        device_kind = device_id[0:3] if device_id is not None else None
        if kinds is not None and device_kind not in kinds:
            return None
        file_id = file_json["id"]
        if file_ids is not None and file_id not in file_ids:
            return None

        def valid_timestamp(timestamp):
            # Convert to integer if it's a string
            if isinstance(timestamp, str):
                try:
                    timestamp = int(timestamp)
                except ValueError:
                    return 0
            # Assuming a valid timestamp should not be larger than a certain threshold
            max_valid_timestamp = 9999999999
            return timestamp if timestamp < max_valid_timestamp else 0

        start_stamp = valid_timestamp(start_stamp)
        end_stamp = valid_timestamp(end_stamp)
        utt = valid_timestamp(utt)

        return {
            "fileId": file_id,
            "fileName": file_json.get("fileName"),
            "fileSize": file_json.get('fileSize'),
            "subjectId": participant,
            "deviceKind": device_kind,
            "deviceId": device_id,
            "timeStart": datetime.fromtimestamp(start_stamp * 0.001).strftime(
                "%Y-%m-%d %H:%M:%S") if start_stamp != 0 else None,
            "timeEnd": datetime.fromtimestamp(end_stamp * 0.001).strftime(
                "%Y-%m-%d %H:%M:%S") if end_stamp != 0 else None,
            "timeUpload": datetime.fromtimestamp(utt * 0.001).strftime(
                "%Y-%m-%d %H:%M:%S") if utt != 0 else None,
            "stampStart": start_stamp,
            "stampEnd": end_stamp,
            "stampUpload": utt,
            "uploadedBy": file_json.get('life', {}).get('createdUser'),
            "uploadTime": file_json.get('life', {}).get('createdTime'),
            "studyId": file_json.get("studyId"),
            "hash": file_json.get("hash")
        }

def field_json_reformat(field_json):
    new_field = deepcopy(field_json)
    new_field['possibleValues'] = new_field.get('categoricalOptions', [])
    new_data_type = 'str'
    if field_json['dataType'] == 'INTEGER':
        new_data_type = 'int'
    elif field_json['dataType'] == 'DECIMAL':
        new_data_type = 'dec'
    elif field_json['dataType'] == 'STRING':
        new_data_type = 'str'
    elif field_json['dataType'] == 'BOOLEAN':
        new_data_type = 'bool'
    elif field_json['dataType'] == 'DATETIME':
        new_data_type = 'date'
    elif field_json['dataType'] == 'FILE':
        new_data_type = 'file'
    elif field_json['dataType'] == 'JSON':
        new_data_type = 'json'
    elif field_json['dataType'] == 'CATEGORICAL':
        new_data_type = 'cat'
    else:
        new_data_type = 'str'
    new_field['dataType'] = new_data_type
    new_field['dateAdded'] = field_json.get('life', {}).get('createdTime')
    new_field['dateDeleted'] = field_json.get('life', {}).get('deletedTime')
    if 'categoricalOptions' in new_field:
        del new_field['categoricalOptions']
    new_field['tableName'] = field_json.get('metadata', {}).get('table')
    return new_field

def get_field_id_from_device_id(device_id: str):
    mapping = {
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

    field_id = mapping.get(device_id, None)
    if field_id is None:
        field_id = device_id
    else:
        return 'Device_' + '_'.join(field_id.split(' '))

def convert_v2_data_clip_input_to_v3(dataclips):
    return [
        {
            "fieldId": el["fieldId"],
            "value": el["value"],
            "properties": {
                "subjectId": el["subjectId"],
                "visitId": el["visitId"]
            }
        }
        for el in dataclips
    ]

def convert_to_date(value):
    if value == '' or pd.isna(value):
        return value  # Return the value unchanged if it's an empty string or NaN
    else:
        return pd.to_datetime(value).date()  # Convert to date and return the date part

def convert_to_date_single(value):
    """
    Convert a date string in ISO format to yyyy-mm-dd format.
    
    Args:
        value: Input date string in format like "2024-08-13T00:00:00.000000"
                
    Returns:
        str: Date in YYYY-MM-DD format, or original string if conversion fails
    """
    if not value or value == '' or pd.isna(value):
        return value  # Return the value unchanged if it's empty or None
    
    try:
        # Parse the datetime and convert to yyyy-mm-dd format
        return pd.to_datetime(value).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        # Return original if conversion fails
        return value
