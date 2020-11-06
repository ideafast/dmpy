# Credentials abstractions

from __future__ import annotations

from typing import Dict, Any, Optional, List, Union, Callable
from abc import ABC, abstractmethod, abstractproperty

from ideafast_dmp.dmp_login_state import DmpLoginState


class DmpCredentials(ABC):

    def __init__(self):
        """
        Create a credentials base instance
        """
        pass

    def add_headers(self, headers: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Add the authentication headers to the 'headers' dictionary and returns it.
        """
        if headers is None:
            headers = {}
        return self._add_headers(headers)

    @abstractmethod
    def _add_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Subclasses add the HTTP authentication headers here
        """
        raise NotImplementedError('this is an abstract method')

    @property
    @abstractmethod
    def is_logged_in(self) -> bool:
        """
        Return true if these credentials represent a logged in user (as
        far as can be known without checking the server).
        Returning false indicates an anonymous user.
        """
        raise NotImplementedError('this is an abstract method')

    @property
    @abstractmethod
    def user_name(self) -> str:
        """
        Return the user name for the logged in user.
        """
        raise NotImplementedError('this is an abstract method')

    @property
    @abstractmethod
    def user_id(self) -> str:
        """
        Return the user ID for the logged in user. Note that this is an
        identifier that is typically not known by the user themselves.
        """
        raise NotImplementedError('this is an abstract method')

    @staticmethod
    def from_state(appname: str) -> DmpCredentials:
        return StateCredentials(appname)

    pass


class StateCredentials(DmpCredentials):

    def __init__(self, appname: str):
        super().__init__()
        self._loginstate = DmpLoginState(appname)

    def _add_headers(self, headers: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_logged_in:
            raise ValueError("You are not logged in")
        headers["Cookie"] = "connect.sid=" + self._loginstate.cookie
        return headers

    @property
    def is_logged_in(self) -> bool:
        """
        True if login info is available. Whether or not that info is valid is up
        to the server to decide
        """
        return self._loginstate.is_logged_in

    @property
    def user_name(self) -> str:
        """
        Return the user name for the logged in user.
        """
        return self._loginstate.username

    @property
    def user_id(self) -> str:
        """
        Return the user ID for the logged in user. Note that this is an
        identifier that is typically not known by the user themselves.
        """
        if self._loginstate.is_logged_in:
            info = self._loginstate.user_info
            return info.userid if info is not None else None
