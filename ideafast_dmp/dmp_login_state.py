from datetime import datetime
from typing import Any, Dict, Optional

from ideafast_dmp.app_state_persistence.app_state import AppState, NamedAppState
from ideafast_dmp.dmp_user_info import DmpUserInfo


class DmpLoginState:
    """
    Helper object to represent a persisted login state for the
    IDEA-FAST Data Management Platform
    """

    def __init__(self, appname: str):
        """
        Create a new Dmp
        :param appname: The name of the application on behalf of whom
        this object manages the DMP login state. Must be a valid identifier.
        """
        self._appstate = AppState(appname).wrap_state("login")
        self._state: Dict[str, Any] = {
            "username": None,
            "cookie": None,
            "info": None,
            "study": None,
        }
        self._reset(True)
        pass

    @property
    def username(self) -> Optional[str]:
        """
        Return the persisted user name, or None if not set
        :return: The user name
        """
        return self._state.get("username", None)

    @property
    def cookie(self) -> Optional[str]:
        """
        Return the persisted login cookie, or None if not "logged in"
        :return: The cookie value
        """
        return self._state.get("cookie", None)

    @property
    def default_study(self) -> Optional[str]:
        """
        Return the default study ID, if any
        """
        return self._state.get("study", None)

    @property
    def info(self) -> Optional[Dict[str, Any]]:
        """
        Return the raw persisted user info object, or None if not "logged in"
        :return: The info dictionary (extracted from the JSON server response)
        """
        return self._state.get("info", None)

    @property
    def user_info(self) -> Optional[DmpUserInfo]:
        """
        Return the user info object reinterpreted as a DmpUserInfo instance,
        or None if not available
        """
        info = self.info
        if info is None:
            return None
        else:
            return DmpUserInfo(info)

    def _save(self):
        self._appstate.save_state(self._state)

    def _reset(self, load: bool):
        state: Dict[str, Any] = {}
        if load:
            state2 = self._appstate.load_state()
            if state2 is not None:
                state = state2
        if "username" not in state:
            state["username"] = None
        if "cookie" not in state:
            state["cookie"] = None
        if "info" not in state:
            state["info"] = None
        if "study" not in state:
            state["study"] = None
        self._state = state
        pass

    def _erase(self):
        """
        Delete the state
        """
        self._appstate.save_state(None)
        self._reset(True)

    def change_user(
        self,
        username: Optional[str],
        cookie: Optional[str],
        info: Optional[Dict[str, Any]],
    ):
        """
        Change the user name and clear or change the login cookie.
        Unless a cookie is provided, calling this implies "logging out"
        :param username: The name of the user, or None to log out and forget the
        username
        :param cookie: The login cookie, or None to log out. Must be None if
        username is None. Default None
        :param info: The login state information received from the server
        """
        if cookie is None and info is not None:
            raise ValueError("Cannot set login info if there is no login cookie")
        if username is None:
            if cookie is not None:
                raise ValueError(
                    "Cannot login without providing a user name at the same time"
                )
            self._reset(False)
            self._save()
        else:
            old_study = self.default_study  # try to preserve it if possible
            self._reset(False)
            self._state["username"] = username
            self._state["cookie"] = cookie
            self._state["info"] = info
            self._state["study"] = None
            if old_study is not None:
                inf2 = self.user_info
                if inf2 is not None:
                    ids = inf2.matching_study_ids(old_study)
                    if len(ids) == 1:
                        self._state["study"] = ids[0]
            self._save()

    def change_study(self, study_prefix: Optional[str]):
        """
        Change the default study ID (or clear it)
        :param study_prefix: A prefix of the new default study ID
        """
        if study_prefix is None or study_prefix == "":
            self._state["study"] = None
        else:
            info = self.user_info
            if info is None:
                raise ValueError(
                    "Cannot validate study ID because you are not logged in"
                )
            ids = info.matching_study_ids(study_prefix)
            if len(ids) == 0:
                raise ValueError(
                    f'Accessible study not found in your login data for study prefix "{study_prefix}"'
                )
            if len(ids) > 1:
                raise ValueError(
                    f'Ambiguous study prefix "{study_prefix}". Matches: {", ".join(ids)}'
                )
            study_id = ids[0]
            self._state["study"] = study_id
            self._save()
        pass

    def login(self, cookie: str, info: Dict[str, Any]):
        """
        Record the login cookie for the current user.
        To set the user name and login cookie at the same time, use "change_user()" instead
        :param cookie: The login cookie, or None to log out
        :param info: The information object received from the server about the user
        """
        if cookie is None:
            self.logout()
        else:
            if self.username is None:
                raise ValueError(
                    'Cannot login without a username (hint: use "change_user" instead of "login")'
                )
            self.change_user(self.username, cookie, info)

    def logout(self):
        """
        Remove the login cookie from the state
        :return:
        """
        self.change_user(self.username, None, None)

    @property
    def is_logged_in(self):
        """
        Returns true if login information is available in this state (whether or not that
        information is valid is up to the server to decide)
        """
        return self.cookie is not None

    @property
    def has_username(self):
        """
        Returns true if a username is available in this state. The username is kept
        even when logged out
        """
        return self.username is not None

    @property
    def state_stamp(self) -> Optional[float]:
        """
        Get the time stamp the login state was last saved at as a unix time code,
        or None if there was no saved state
        """
        return self._appstate.state_stamp

    @property
    def state_datetime(self) -> Optional[datetime]:
        """
        Get the time stamp the login state was last saved at as a datetime in UTC,
        or None if there was no saved state
        """
        return self._appstate.state_datetime

    @property
    def appstate(self) -> NamedAppState:
        """
        The underlying application state proxy
        """
        return self._appstate

    @property
    def state_host(self) -> AppState:
        """
        The host AppState (corresponding to the folder where state files are stored)
        """
        return self._appstate.host

    pass
