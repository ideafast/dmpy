import json
from copy import deepcopy
from datetime import datetime, timezone
import pandas as pd
from typing import Optional
import getpass
import os

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
    'POE': 'Participant Experiences Opinions',
    "DMO": "Derived AX6 Digital Mobility Outcome",
    "HRR": "Derived VTP Heart Recovery Rate Features"
}

device_kinds = list(kinds_mapping.keys())

def load_host_from_file() -> Optional[str]:
    username = getpass.getuser()
    try:
        with open(f'/tmp/{username}/cookie/host', 'r') as f:
            return f.read().strip('\n\r')
    except:
        return None

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
    
    device_id = file_json.get('properties').get("deviceId", None)
    device_kind = device_id[0:3] if device_id is not None else None
    if device_kinds is not None and device_kind not in device_kinds:
        return {
            "fileId": file_json.get('id'),
            "fileName": file_json.get('fileName'),
            "fileSize": file_json.get('fileSize'),
            "timeUpload": utt,
            "stampUpload": _process_timestamp_to_ms(file_json.get('life', {}).get('createdTime')),
            "uploadedBy": file_json.get('life', {}).get('createdUser'),
            "uploadTime": file_json.get('life', {}).get('createdTime'),
            "studyId": file_json.get("studyId"),
            "hash": file_json.get("hash"),
            "properties": file_json.get('properties', {})
        }
    else:
        
        start_stamp = file_json.get('properties', {}).get("startDate", None)
        end_stamp = file_json.get('properties', {}).get("endDate", None)

        participant = file_json.get('properties', {}).get("subjectId", None) or file_json.get('properties', {}).get("participantId", None)
        if participants is not None and participant not in participants:
            return None

        file_id = file_json["id"]
        if file_ids is not None and file_id not in file_ids:
            return None
                
        start_stamp = valid_timestamp(start_stamp)
        end_stamp = valid_timestamp(end_stamp)
        utt = valid_timestamp(utt)
        start_time = start_stamp[:10].replace('-', '') if start_stamp is not None else 'NANANANA'
        end_time = end_stamp[:10].replace('-', '') if end_stamp is not None else 'NANANANA'
        return {
            "fileId": file_id,
            "fileName": f"{participant.replace('-', '')}-{device_id}-{start_time}-{end_time}.{file_json.get('fileName').split('.')[-1]}",
            "fileSize": file_json.get('fileSize'),
            "subjectId": participant.replace('-', ''),
            "participantId": participant.replace('-', ''),
            "deviceKind": device_kind,
            "deviceId": device_id,
            "timeStart": start_stamp,
            "timeEnd": end_stamp,
            "timeUpload": utt,
            "stampStart": _process_timestamp_to_ms(file_json.get('properties', {}).get("startDate", None)),
            "stampEnd": _process_timestamp_to_ms(file_json.get('properties', {}).get("endDate", None)),
            "stampUpload": _process_timestamp_to_ms(file_json.get('life', {}).get('createdTime')),
            "uploadedBy": file_json.get('life', {}).get('createdUser'),
            "uploadTime": file_json.get('life', {}).get('createdTime'),
            "studyId": file_json.get("studyId"),
            "hash": file_json.get("hash"),
            "properties": file_json.get('properties', {})
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
        'POE': 'Participant Experiences Opinions',
        "HRR": "Derived VTP Heart Recovery Rate Features"
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

def format_size(bytes_size: int) -> str:
    """
    Function to format a size in bytes to a human-readable format
    """
    # Define units and their corresponding sizes
    units = ["B", "KB", "MB", "GB", "TB"]
    size = bytes_size
    index = 0

    # Loop to divide by 1024 and move up the units
    while size >= 1024 and index < len(units) - 1:
        size /= 1024.0
        index += 1
    
    # Return the size formatted to 2 decimal places
    return f"{size:.2f} {units[index]}"

def _process_timestamp_to_ms(timestamp):
    """
    Process various timestamp formats to millisecond timestamp.
    Helper function for valid_timestamp.
    
    Args:
        timestamp: Input timestamp in various formats
        
    Returns:
        int: Unix timestamp in milliseconds
    """
    # If it's already an integer or float, validate the timestamp
    if isinstance(timestamp, (int, float)):
        return _validate_numeric_timestamp(timestamp)
        
    # Handle string timestamps
    if isinstance(timestamp, str):
        # Try parsing as integer first (for unix timestamps in string form)
        try:
            numeric_timestamp = int(timestamp)
            return _validate_numeric_timestamp(numeric_timestamp)
        except ValueError:
            pass
        
        # Try parsing as date string
        try:
            # Handle common date formats
            if len(timestamp) == 8 and timestamp.isdigit():  # yyyymmdd
                dt = datetime.strptime(timestamp, '%Y%m%d')
            elif len(timestamp) == 10 and '-' in timestamp:  # yyyy-mm-dd
                dt = datetime.strptime(timestamp, '%Y-%m-%d')
            else:  # Try parsing other formats
                dt = pd.to_datetime(timestamp)
            
            # Normalize time to midnight (00:00:00) and set timezone to UTC
            dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
            # Convert to unix timestamp (milliseconds)
            return int(dt.timestamp() * 1000)
        except (ValueError, TypeError):
            return 0
    
    return 0

def _validate_numeric_timestamp(timestamp):
    # Define thresholds
    max_seconds_timestamp = 9999999999  # ~March 2286
    max_millis_timestamp = 9999999999999  # ~November 2286
    
    # Check if the number might be a YYYYMMDD format
    if 19000101 <= timestamp <= 21000101 and len(str(int(timestamp))) == 8:
        # Convert YYYYMMDD to datetime
        year = int(timestamp) // 10000
        month = (int(timestamp) % 10000) // 100
        day = int(timestamp) % 100
        try:
            # Create datetime at midnight UTC
            dt = datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)  # Convert to milliseconds
        except ValueError:
            pass  # If invalid date, continue with regular timestamp validation
    
    # Check if timestamp is valid based on size
    if timestamp <= 0:
        return 0
    elif timestamp <= max_seconds_timestamp:
        return timestamp * 1000  # Convert seconds to milliseconds
    elif timestamp <= max_millis_timestamp:
        return timestamp  # Already in milliseconds
    else:
        return 0  # Invalid timestamp (too large)

def valid_timestamp(timestamp):
        """
        Convert various timestamp formats to YYYYMMDD string with time normalized to 00:00:00.
        Handles Unix timestamps (seconds/milliseconds), YYYYMMDD as int or string, and date strings.
        
        Args:
            timestamp: Timestamp in various formats (Unix timestamp, YYYYMMDD, date string)
            
        Returns:
            str: Formatted date string as YYYYMMDD or None if invalid/empty
        """
        # Handle None or empty values
        if timestamp is None or timestamp == '':
            return None
            
        # Process timestamp to get millisecond timestamp
        ms_timestamp = _process_timestamp_to_ms(timestamp)
        
        # Convert millisecond timestamp to formatted string
        if ms_timestamp == 0:
            return None
        else:
            # Convert to datetime and normalize to midnight (00:00:00)
            dt = datetime.fromtimestamp(ms_timestamp * 0.001, timezone.utc)
            # Reset time to 00:00:00
            dt = datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S")