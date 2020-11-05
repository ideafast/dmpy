# (c) VTT / ttelcl 2020

# This file contains the code related to the folder caching and
# indexing downloaded data files

from typing import Optional, Dict, List, Union, Any
from ideafast_dmp.app_state_persistence.app_state import NamedAppState, AppState
from ideafast_dmp.dmp_utils import safe_dict_get
from pathlib import Path


class DmpDataCache:
    """
    Tracks the location of the data cache in a user-specific persisted setting
    """

    def __init__(self, appname: Optional[str]):
        """
        Create a new DmpDataCache object
        :param appname: (optional) A name for the application. This is used
        to derive the name of the folder where the settings file is stored
        that, in turn, stores the location of the data folder. If not None,
        this must be a valid ID. Default: 'dmp_data'
        """
        appname = appname or "dmp_data"
        self._settings = AppState(appname).wrap_state("dmp_cache")
        self._state: Dict[str, Any] = self._settings.load_state()
        if self._state is None:
            self._state: Dict[str, Any] = {"data_folder": None}
            self._settings.save_state(self._state)
        pass

    @property
    def data_folder_raw(self) -> Optional[str]:
        """
        Get the name of the configured data folder, or None if not
        configured
        """
        return safe_dict_get(self._state, "data_folder")

    @property
    def data_folder(self) -> Path:
        """
        Get the path of the data folder. This property raises an exception if
        that has not been configured yet. As a side effect, it ensures that
        the data folder exists (creating it if necessary)
        """
        fname = self.data_folder_raw
        if fname is None or fname == "":
            raise ValueError("Data folder has not been configured yet")
        folder = Path(fname)
        if not folder.is_absolute():
            raise ValueError(
                f'Expecting the configured data path to be absolute, but got "{folder}"'
            )
        if not folder.exists():
            folder.mkdir()
        if not folder.is_dir():
            raise ValueError(f'"{folder}" is not a folder')
        return folder

    @property
    def is_configured(self) -> bool:
        """
        Returns True if a data folder has been configured
        """
        fname = self.data_folder_raw
        return fname is not None and fname != ""

    def configure_data_folder(self, new_data_folder: str):
        """
        Change (or initialize) the data folder path.
        :param new_data_folder: The data folder, which must be an absolute path. If the
        folder does not yet exist, this method creates it.
        """
        path = Path(new_data_folder)
        if not path.is_absolute():
            raise ValueError(f'Expecting an absolute path but got "{path}"')
        path.mkdir(exist_ok=True)
        self._state["data_folder"] = str(path)
        self._settings.save_state(self._state)

    pass
