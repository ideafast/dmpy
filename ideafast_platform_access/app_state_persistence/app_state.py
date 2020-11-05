# Helper functions for saving and loading an 'application state'
# Application state is saved as JSON files in an app-specific subfolder of the
# user's home folder

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Optional, Union
from datetime import datetime, timezone
from os import PathLike


class AppState:
    def __init__(self, appname: str):
        """
        Create a new AppState using the specified application name to determine
        the folder to save state files to
        :param appname: The application name
        """
        if not(appname.isidentifier()):
            raise ValueError(f'"{appname}" is not a valid appname (expecting an identifier)')
        self._appname = appname
        self._apphome = Path.home().joinpath('.' + appname)
        self._apphome.mkdir(parents=True, exist_ok=True)
        pass

    @property
    def home(self) -> Path:
        """
        Return the application state folder
        :return: The application state folder
        """
        return self._apphome

    def appname(self) -> str:
        """
        Retrieve the name of the app for this AppState (determining the name
        of the folder the states are saved to)
        :return: The application name
        """
        return self._appname

    def wrap_state(self, statename: str) -> NamedAppState:
        """
        Create a new NamedAppState that exposes this AppState's methods
        for a fixed state name.
        :param statename: The name of the state to manage (determining
        the state file name)
        :return: A new NamedAppState
        """
        return NamedAppState(self, statename)

    def state_file_name(self, state_name: str) -> Path:
        """
        Get the full path to the file where the given state will be saved to or
        will be loaded from
        """
        return self.home.joinpath(state_name + '.json')

    def save_state(self, name: str, state: Any):
        """
        Save a state object to a named state.
        :param name: The name of the state, which must be a valid identifier
        :param state: The state object, which must be convertible to JSON. Or None
        to delete an existing named state
        :return: Returns None
        """
        if not(name.isidentifier()):
            raise ValueError(f'"{name}" is not a a valid app state identifier')
        statefile = self.home.joinpath(name + '.json')
        tmpfile = statefile.with_suffix(".tmp")
        if state is None:
            # soft-delete: move it to the backup file
            if statefile.exists():
                bakfile = statefile.with_suffix('.bak')
                statefile.replace(bakfile)
            pass
        else:
            with tmpfile.open('w') as tf:
                json.dump(state, tf, indent=2)
            if statefile.exists():
                bakfile = statefile.with_suffix('.bak')
                statefile.replace(bakfile)
            tmpfile.replace(statefile)
        pass

    def load_state(self, name: str, default: Any = None) -> Any:
        """
        Load a state object from a named state (converting it back from JSON)
        :param name: The name of the state, which must be a valid identifier
        :param default: The value to return if there was no saved state (default None)
        :return: The saved state object, converted back from JSON, or the default
        argument if there was no state saved
        """
        if not(name.isidentifier()):
            raise ValueError(f'"{name}" is not a a valid app state identifier')
        statefile = self.home.joinpath(name + '.json')
        if not(statefile.exists()):
            return default
        else:
            with statefile.open('r') as sf:
                state = json.load(sf)
            return state

    def state_stamp(self, name: str) -> Optional[float]:
        """
        Return the last modified timestamp of the named state as a floating point UNIX
        time code, or None if not present.
        :param name: The name of the state (a valid identifier)
        :return: The time stamp as a UNIX-like time code (seconds since
        1970-01-01 00:00:00 UTC) or None
        """
        if not(name.isidentifier()):
            raise ValueError(f'"{name}" is not a a valid app state identifier')
        # The type annotation is to stop PyCharm 2020.1 from showing incorrect use warnings
        statefile: Union[Path, PathLike] = self.home.joinpath(name + '.json')
        if not(statefile.exists()):
            return None
        else:
            return os.path.getmtime(statefile)

    def state_datetime(self, name: str) -> Optional[datetime]:
        """
        Return the last modified timestamp of the named state as a datetime instance,
        or None if not present.
        :param name: The name of the state (a valid identifier)
        :return: The time stamp as a datetime in the UTC timezone, or None
        """
        if not(name.isidentifier()):
            raise ValueError(f'"{name}" is not a a valid app state identifier')
        # The type annotation is to stop PyCharm 2020.1 from showing incorrect use warnings
        statefile: Union[Path, PathLike] = self.home.joinpath(name + '.json')
        if not(statefile.exists()):
            return None
        else:
            ts = os.path.getmtime(statefile)
            return datetime.fromtimestamp(ts, timezone.utc)
        pass

    pass


class NamedAppState:
    """
    Combines an AppState with a fixed state name, enabling a more compact
    access API
    """
    def __init__(self, host: AppState, statename: str):
        self._host = host
        self._statename = statename
        if not(statename.isidentifier()):
            raise ValueError('The state name must be a valid identifier')
        pass

    @property
    def host(self) -> AppState:
        """
        Retrieve the AppState object that hosts this NamedAppState
        :return: The AppState object
        """
        return self._host

    @property
    def statename(self) -> str:
        """
        Retrieve the name for the state managed by this NamedAppState
        :return: The state name
        """
        return self._statename

    @property
    def state_file_name(self) -> Path:
        """
        Get the full path of the file backing the state
        """
        return self._host.state_file_name(self._statename)

    def save_state(self, state: Any):
        """
        Save a state object to this named state.
        :param state: The state object, which must be convertible to JSON. Or None
        to delete an existing named state
        :return: Returns None
        """
        self._host.save_state(self._statename, state)

    def load_state(self, default: Any = None) -> Any:
        """
        Load a state object from this named state (converting it back from JSON)
        :param default: The value to return if there was no saved state (default None)
        :return: The saved state object, converted back from JSON, or the default
        argument if there was no state saved
        """
        return self._host.load_state(self._statename, default)

    @property
    def state_stamp(self) -> Optional[float]:
        """
        The last modified timestamp of the named state as a floating point UNIX
        time code, or None if not present.
        :return: The time stamp as a UNIX-like time code (seconds since
        1970-01-01 00:00:00 UTC) or None
        """
        return self._host.state_stamp(self._statename)

    @property
    def state_datetime(self) -> Optional[datetime]:
        """
        The last modified timestamp of the named state as a datetime instance,
        or None if not present.
        :return: The time stamp as a datetime in the UTC timezone, or None
        """
        return self._host.state_datetime(self._statename)


