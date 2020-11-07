from __future__ import annotations

import json
from datetime import datetime, timezone
from os import PathLike
from pathlib import Path
from typing import Any, List, Optional, Union


def safe_dict_get(d: dict, k: str) -> Any:
    if d is None:
        return None
    else:
        return d.get(k, None)


def safe_list_get(a: List, idx: int) -> Any:
    if a is None or idx < 0 or idx >= len(a):
        return None
    else:
        return a[idx]


def save_json_with_backup_old(fnm: Union[str, Path], obj: Any):
    outfile = Path(fnm)
    tmpfile = outfile.with_suffix(".tmp")
    if obj is None:
        # soft-delete: move it to the backup file
        if outfile.exists():
            bakfile = outfile.with_suffix(".bak")
            outfile.replace(bakfile)
        pass
    else:
        with tmpfile.open("w") as tf:
            json.dump(obj, tf, indent=2)
        if outfile.exists():
            bakfile = outfile.with_suffix(".bak")
            outfile.replace(bakfile)
        tmpfile.replace(outfile)
    pass


def save_json_with_backup(fnm: Union[str, Path], obj: Any):
    with FileTransaction.start(fnm) as trx:
        with trx.tmp_name.open("w") as tf:
            json.dump(obj, tf, indent=2)
        trx.commit()
    pass


def stamp_to_text(stamp: Optional[int]) -> Optional[str]:
    """
    Convert a time in UNIX milliseconds format to an ISO string
    """
    if stamp is None:
        return None
    else:
        dt = datetime.fromtimestamp(stamp * 0.001, timezone.utc)
        return dt.isoformat("T", "milliseconds")


def stamp_to_datetime(stamp: Optional[int]) -> Optional[datetime]:
    """
    Convert a time in UNIX milliseconds format to a datetime instance in the UTC time zone
    """
    if stamp is None:
        return None
    else:
        dt = datetime.fromtimestamp(stamp * 0.001, timezone.utc)
        return dt


class FileTransaction:
    """
    Helper for safely writing a file. This context manager helps you
    write to a temporary file, then commit the written content to the
    real file name on success (and create a backup), or abort
    and not modify the target file
    """

    def __init__(self, target_file_name: Union[str, Path, PathLike]):
        self._target = Path(target_file_name)
        self._tmp_name = self._target.with_name(self._target.name + ".tmp")
        self._bak_name = self._target.with_name(self._target.name + ".bak")
        self._committed = False
        pass

    @property
    def target_name(self) -> Path:
        """
        Get the final target file name (as a Path instance). Calling commit() will copy
        self.tmp_name to this
        """
        return self._target

    @property
    def tmp_name(self) -> Path:
        """
        Get the name of the temporary file you are expected to write to (as a Path instance)
        """
        return self._tmp_name

    @classmethod
    def start(cls, target_file_name: Union[str, Path, PathLike]) -> FileTransaction:
        """
        Start a new file transaction. Call this inside a 'with' statement; write your
        content to the 'tmp_name' of the returned transaction object, then 'commit()'
        it after closing the file.

        :param target_file_name: the name of the final file

        Example:
            .. code-block:: python

                def save_json_with_backup(fnm: Union[str, Path], obj: Any):
                    with FileTransaction.start(fnm) as trx:
                        with trx.tmp_name.open('w') as tf:
                            json.dump(obj, tf, indent=2)
                        trx.commit()
                    pass
        """
        return FileTransaction(target_file_name)

    def commit(self):
        """
        Moves the temporary file to the final target file. If the target file
        already existed, it is moved to the backup file first (replacing the
        original backup file if it existed)
        :return: None
        """
        if self._committed:
            raise ValueError("The file transaction was already committed")
        self._committed = True
        if not self.tmp_name.is_file():
            # soft-delete: move target to the backup file without creating a new
            # target
            if self.target_name.is_file():
                self.target_name.replace(self._bak_name)
            pass
        else:
            if self.target_name.is_file():
                self.target_name.replace(self._bak_name)
            self.tmp_name.replace(self.target_name)

    def rollback(self):
        """
        Abort the file transaction. Marks this transaction as complete if it wasn't
        already, without shuffling around any files
        :return: None
        """
        self._committed = True

    def __enter__(self) -> FileTransaction:
        """
        Infrastructure for calling by 'with' statement. Returns self
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up
        """
        if not self._committed:
            self.rollback()
        pass

    pass
