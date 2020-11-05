
from __future__ import annotations

from typing import Union, Any, Dict, List, Optional, Iterable

import pandas as pd
import json
from pathlib import Path
from os import PathLike

from .dmp_connection import DmpConnection
from .dmp_data_cache import DmpDataCache
from .dmp_utils import stamp_to_text, stamp_to_datetime


class DmpFileInfo:
    """
    Information about a file available for download
    """

    def __init__(
            self,
            file_id: str,
            file_name: str,
            file_size: int,
            participant_id: str,
            device_id: str,
            stamp_start: int,
            stamp_end: int,
            stamp_upload: int,
            study_id: str):
        self.file_id = file_id
        self.file_name = file_name
        self.file_size = file_size
        self.participant_id = participant_id
        self.device_kind = device_id[0:3] if device_id is not None else None
        self.device_id = device_id
        self.stamp_start = stamp_start
        self.stamp_end = stamp_end
        self.stamp_upload = stamp_upload
        self.t_start = stamp_to_text(stamp_start)
        self.t_end = stamp_to_text(stamp_end)
        self.t_upload = stamp_to_text(stamp_upload)
        self.study_id = study_id
        pass

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> DmpFileInfo:
        """
        Create a DmpFileInfo from a record loaded from a study.*.files.json file
        """
        return DmpFileInfo(
            d['fileId'],
            d['fileName'],
            d['fileSize'],
            d['participantId'],
            d['deviceId'],
            d['stampStart'],
            d['stampEnd'],
            d['stampUpload'],
            d.get('studyId')
        )

    def path_name(self) -> Path:
        """
        Return the relative path where the file should be saved (relative to the
        data folder)
        """
        return Path(self.participant_id, self.device_id, self.file_name)

    pass


class DmpFileSet:
    """
    A collection of DmpFileInfo records, indexed by file id
    """

    def __init__(self, records: Iterable[DmpFileInfo]):
        self._record_map: Dict[str, DmpFileInfo] = {r.file_id: r for r in records}
        pass

    @staticmethod
    def from_dicts(dicts: List[Dict[str, Any]]) -> DmpFileSet:
        """
        Create a DmpFileSet from the data loaded from a study.*.files.json file
        """
        return DmpFileSet((DmpFileInfo.from_dict(d) for d in dicts))

    def by_id(self, file_id: str) -> Optional[DmpFileInfo]:
        """
        Find a file record by its file id, returning None if not found
        """
        return self._record_map.get(file_id)

    @property
    def file_map(self) -> Dict[str, DmpFileInfo]:
        """
        Get the dictionary that maps file ids to records
        :return:
        """
        return self._record_map

    def all(self) -> Iterable[DmpFileInfo]:
        """
        Return all records
        """
        for record in self._record_map.values():
            yield record

    def project_ids_sequence(self, ids: Iterable[str]) -> Iterable[DmpFileInfo]:
        """
        Look up all of the given file IDs, returning DmpFileRecords for all
        that were found (missing records are skipped)
        """
        for fid in ids:
            record = self._record_map.get(fid)
            if record is not None:
                yield record

    def project_ids(self, ids: Iterable[str]) -> DmpFileSet:
        """
        Like project_ids_sequence, but storing the records in a new
        DmpFileSet
        :return: a new DmpFileSet containing only the selected records
        """
        return DmpFileSet(self.project_ids_sequence(ids))

    def matching_id(self, id_prefix: str) -> Iterable[DmpFileInfo]:
        """
        Returns file records whose file id starts with the given prefix
        """
        id_prefix = id_prefix.lower()
        for file_id, record in self._record_map.items():
            if file_id.lower().startswith(id_prefix):
                yield record

    pass


class DmpFileDb:
    """
    A database of files available on the server
    """

    def __init__(self, cache: DmpDataCache = None):
        """
        Create a new DmpFileDb
        :param cache: The cache representing the data folder, or None to use the
        default data folder
        """
        self._cache = cache or DmpDataCache(None)
        pass

    def study_files(self, study: str) -> Optional[pd.DataFrame]:
        """
        Return a DataFrame describing all files in the study. The list must already have been
        stored in the data folder in JSON form
        :param study: The full study ID
        :return: A data frame describing all files in the study, or None if the data
        description file was missing.
        """
        dbfile = self._cache.data_folder / f'study.{study}.files.json'
        if not dbfile.is_file():  # without this explicit check pandas acts weird for missing files
            return None
        df = pd.read_json(dbfile, orient='records')
        return df

    def study_file_set(self, study: str) -> DmpFileSet:
        """
        Return a DmpFileSet describing all files in the study.
        Raises an exception if the study file is not found
        :param study: The full study ID
        :return: A DmpFileSet containing the DmpFileInfo records for the study.
        """
        dbfile = self._cache.data_folder / f'study.{study}.files.json'
        if not dbfile.is_file():
            raise ValueError(f'File not found: {dbfile}')
        with dbfile.open('r') as f:
            records = json.load(f)
        return DmpFileSet.from_dicts(records)

    @staticmethod
    def filter(
            files: pd.DataFrame,
            participant: Optional[Union[str, List[str]]] = None,
            kind: Optional[Union[str, List[str]]] = None,
            device: Optional[Union[str, List[str]]] = None,
            prefix: Optional[Union[str, List[str]]] = None) -> pd.DataFrame:
        """
        Return a filtered version of the input file list
        :param files: The input file list
        :param participant: If not None, only return records for matching participant id(s)
        :param kind: If not None, only return records for matching device kind(s)
        :param device: If not None, only return records for matching full device name(s)
        :param prefix: If not None, only return record(s) matching the file id prefix(es)
        :return: a dataframe containing a subset of the input data frame records
        """
        df = files
        if participant is not None:
            if isinstance(participant, list):
                participant = [p.upper() for p in participant]
                df = df.loc[df.participantId.isin(participant)]
            else:
                df = df.loc[df.participantId.eq(participant.upper())]
        if kind is not None:
            if isinstance(kind, list):
                kind = [k.upper() for k in kind]
                df = df.loc[df.deviceKind.isin(kind)]
            else:
                df = df.loc[df.deviceKind.eq(kind.upper())]
        if device is not None:
            if isinstance(device, list):
                device = [d.upper() for d in device]
                df = df.loc[df.deviceId.isin(device)]
            else:
                df = df.loc[df.deviceId.eq(device.upper())]
        if prefix is not None:
            if isinstance(prefix, list):
                prefix = [p.lower() for p in prefix]
                df = df.loc[df.fileId.apply(lambda s: any(s.startswith(p.lower()) for p in prefix))]
            else:
                df = df.loc[df.fileId.apply(lambda s: s.startswith(prefix.lower()))]
        return df

    @staticmethod
    def extract_ids(files: pd.DataFrame, fid_column_name: str = 'fileId'):
        """
        Extract the file ids from the data frame that contains a "fileId" column
        """
        for idx, row in files.iterrows():
            fid = row[fid_column_name]
            if fid is not None:
                yield fid

    def is_up_to_date(self, dfi: DmpFileInfo) -> bool:
        """
        Check if the locally cached copy of the given file exists and matches the
        properties
        """
        full_path = self._cache.data_folder / dfi.path_name()
        if full_path.is_file():
            stats = full_path.stat()
            if stats.st_size != dfi.file_size:
                return False
            millis = stats.st_mtime_ns / 100000
            if millis < dfi.stamp_upload:
                return False
            return True
        return False

    def download(self,
                 dc: DmpConnection,
                 dfi: DmpFileInfo,
                 force_overwrite: bool,
                 use_id_name: bool = False,
                 name_override: Optional[Union[str, Path, PathLike]] = None) -> Optional[Path]:
        """
        Download a data file from the server
        :param dc: The connection descriptor - representing the currently logged in user
        :param dfi: Identifies and describes the data file to download
        :param force_overwrite: Determines the behaviour when the output file already exists.
        If True, the file is re-downloaded and overwritten. If False, the download is skipped,
        and None is returned.
        :param use_id_name: Default False. If True, use a file name based on file ID instead of the
        original file name
        :param name_override: If not None then explictly use this file name instead of the automatically
        determined one
        :return: The path to the newly written file, or None if the download was skipped
        """

        raise NotImplementedError('Download not yet implemented')
        pass

    pass

