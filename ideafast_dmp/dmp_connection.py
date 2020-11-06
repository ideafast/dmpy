# interaction with the DMP server

from __future__ import annotations

import http.client
import json
import re
from typing import Dict, Any, Optional, List, Union, Callable
from http.cookies import SimpleCookie, Morsel
from pathlib import Path
from abc import ABC, abstractmethod, abstractproperty

from ideafast_dmp.dmp_resources import read_text_resource
from ideafast_dmp.dmp_login_state import DmpLoginState
from ideafast_dmp.dmp_utils import safe_dict_get, safe_list_get, stamp_to_text


class DmpGqlResponse:
    def __init__(self, status: int, jsontext: str, cookies: SimpleCookie):
        self._status = status
        self._json = jsontext
        self._cookies = cookies
        pass

    @property
    def status(self) -> int:
        """
        The HTTP status code
        """
        return self._status

    @property
    def jsontext(self) -> str:
        """
        The response content (presumably JSON) in text form
        """
        return self._json

    @property
    def cookies(self) -> SimpleCookie:
        """
        The cookies that were set by the server
        """
        return self._cookies

    def cookies_as_dict(self) -> Dict[str, str]:
        """
        Return the cookies as a simplified string-string mapping.
        [[CURRENTLY THE VALUES MAY BE WRONG]]
        :return:
        """
        cookiedict = {}
        if self.cookies is not None:
            for k, v in self.cookies.items():
                morsel: Morsel = v
                cookiedict[k] = morsel.coded_value
        return cookiedict

    pass


class DmpResponse:
    """
    Captures the response of a DMP GraphQL query after pre-processing
    """

    def __init__(
            self, content: Dict[str, Any], status: int, cookies: Optional[Dict[str, str]]
    ):
        self._status = status
        self._cookies = cookies or dict()
        self._content = content
        pass

    @property
    def status(self) -> int:
        """
        The HTTP status code
        """
        return self._status

    @property
    def cookies(self) -> Dict[str, str]:
        """
        The collection of cookie set requests from the server
        """
        return self._cookies

    @property
    def content(self) -> Dict[str, Any]:
        """
        The 'content'. Exact specification varies on the call
        """
        return self._content


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


class DmpConnection:
    """
    Represents a connection to the DMP server
    """

    def __init__(self, appname: str, credentials: Optional[DmpCredentials] = None, server: str = None):
        """
        Create a connection to the DMP server. This object acts as its own "context manager",
        so use this constructor in a "with" block
        :param appname: The application name, used to locate the persisted login information
        :param server: The server name or None to use the default ('data.ideafast.eu')
        """
        if server is None:
            server = "data.ideafast.eu"
        self._server = server
        self._credentials = credentials
        self._conn = http.client.HTTPSConnection(self._server)
        if self._credentials is None:
            # TODO: remove this backward compatibility stub
            self._loginstate = DmpLoginState(appname)
        else:
            self._loginstate = None
        pass

    def __enter__(self):
        """
        Supports the Python 'with' statement
        """
        self._conn.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Supports the Python 'with' statement
        """
        self._conn.close()
        return False

    def close(self):
        """
        Close the inner server connection
        """
        self._conn.close()

    @property
    def is_logged_in(self) -> bool:
        """
        True if login info is available. Whether or not that info is valid is up
        to the server to decide
        """
        if self._credentials is not None:
            return self._credentials.is_logged_in
        else:
            # TODO: remove this backward compatibility stub
            return self._loginstate.is_logged_in

    def graphql_request(
            self, query: str, variables: Dict[str, Any], authenticated: bool = True
    ) -> DmpGqlResponse:
        """
        Initiate a request to the DMP server's GraphQL query endpoint
        :param query: The GraphQL query text
        :param variables: The query parameters
        :param authenticated: (default true) If true, add the authentication headers
        and fail if those are missing
        :return: The full JSON text from the response
        """
        headers = {
            "Content-Type": "application/json",
        }
        if authenticated:
            if not self.is_logged_in:
                raise ValueError("You are not logged in")
            if self._credentials is not None:
                headers = self._credentials.add_headers(headers)
            else:
                # TODO: remove this backward compatibility stub
                headers["Cookie"] = "connect.sid=" + self._loginstate.cookie
        payload = {"query": query}
        if variables is not None:
            payload["variables"] = variables
        payloadtext = json.dumps(payload)
        self._conn.request("POST", "/graphql", payloadtext, headers)
        res: http.client.HTTPResponse = self._conn.getresponse()
        data = res.read()
        cookies = SimpleCookie()
        setcookievalue = res.getheader("Set-Cookie")
        if setcookievalue is not None:
            cookies.load(setcookievalue)
        return DmpGqlResponse(res.status, data.decode("utf-8"), cookies)

    def download_file(
            self,
            file_id: str,
            dest: Union[Path, str],
            progress: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Download a single file from the server to the given local destination file (overwriting it if it exists)
        :param file_id: The full file id of the file to download
        :param dest: The destination file name. This must be an absolute path.
        :param progress: An optional progress callback. If not None, this is called repeatedly with the
        number of bytes downloaded so far
        :return: The HTTP status code (200 on success)
        """
        dest = Path(dest)
        if not dest.is_absolute():
            raise ValueError(f"Expecting an absolute path as destination file")
        if (
                re.match(
                    r"^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$",
                    file_id,
                )
                is None
        ):
            raise ValueError(f'Not a valid file ID: "{file_id}"')
        if not self.is_logged_in:
            raise ValueError("You are not logged in")
        directory = dest.parent
        if not directory.is_dir():
            directory.mkdir(parents=True)
        # TODO: replace with credentials based code
        headers = {"Cookie": "connect.sid=" + self._loginstate.cookie}
        self._conn.request("GET", f"/file/{file_id}", None, headers)
        res: http.client.HTTPResponse = self._conn.getresponse()
        if res.status != 200:
            res.close()
            return res.status
        size_so_far = 0
        tmp = dest.parent / f"{dest.name}.tmp"
        with tmp.open("wb") as f:
            more = True
            while more:
                chunk = res.read(65536)
                more = chunk is not None and len(chunk) > 0
                if more:
                    f.write(chunk)
                    size_so_far = size_so_far + len(chunk)
                    if progress is not None:
                        progress(size_so_far)
        tmp.replace(dest)
        return res.status

    def user_info_request(self) -> DmpResponse:
        """
        Request the information record for the "currently logged in user" from
        the server. Raises an exception if there is no currently logged in user.
        Raises an exception if the current user information is no longer considered
        valid by the server.
        :return: A response object. The content is the user info object
        """
        query = read_text_resource("dmp_userinfo.graphql")
        if self._credentials is not None:
            if not self.is_logged_in:
                raise ValueError("You are not logged in")
            userid: str = self._credentials.user_id
        else:
            # TODO: disable this backward compat code
            info = self._loginstate.info
            if info is None or "id" not in info:
                raise ValueError("You are not logged in")
            userid: str = info["id"]
        variables = {"userid": userid}
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")

        # print(f'DEBUG: response content was: {response.jsontext}')

        content: dict = json.loads(response.jsontext)
        data = safe_dict_get(content, "data")
        users = safe_dict_get(data, "getUsers")
        user: Dict[str, Any] = safe_list_get(users, 0)
        retval = DmpResponse(user, response.status, response.cookies_as_dict())
        return retval

    def study_files_request(self, study_id: str) -> List[Dict[str, Any]]:
        """
        Request information on the content of a study (including detailed information
        on each file)
        :param study_id: the full study ID string
        :return: A dictionary with
        """

        def reformat_file_entry(fe: Dict[str, Any], studyname: str) -> Dict[str, Any]:
            dtx: str = fe.get("description")
            description: Dict[str, Any] = json.loads(dtx)
            utt = fe.get("uploadTime")
            if isinstance(utt, str):
                utt = int(utt)
            start_stamp = safe_dict_get(description, "startDate")
            end_stamp = safe_dict_get(description, "endDate")
            device_id: Optional[str] = safe_dict_get(description, "deviceId")
            device_kind = device_id[0:3] if device_id is not None else None
            ret = {
                "fileId":        fe["id"],
                "fileName":      fe.get("fileName"),
                "fileSize":      fe["fileSize"],
                # 'description': description,
                "participantId": safe_dict_get(description, "participantId"),
                "deviceKind":    device_kind,
                "deviceId":      device_id,
                "timeStart":     stamp_to_text(start_stamp),
                "timeEnd":       stamp_to_text(end_stamp),
                "timeUpload":    stamp_to_text(utt),
                "stampStart":    start_stamp,
                "stampEnd":      end_stamp,
                "stampUpload":   utt,
                "uploadedBy":    fe.get("uploadedBy"),
                "studyId":       fe.get("studyId"),
                "studyName":     studyname,
            }
            return ret

        query = read_text_resource("dmp_study_files.graphql")
        if self._credentials is not None:
            if not self._credentials.is_logged_in:
                raise ValueError("You are not logged in")
        else:
            info = self._loginstate.info
            # TODO: remove this backward compatibility stub
            if info is None or "id" not in info:
                raise ValueError("You are not logged in")
        variables = {
            "studyId": study_id,
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        content: dict = json.loads(response.jsontext)
        data = safe_dict_get(content, "data")
        study = safe_dict_get(data, "getStudy")
        study_name: str = safe_dict_get(study, "name")
        files: List[Dict[str, Any]] = safe_dict_get(study, "files")
        if files is None:
            # TODO: remove this backward dependency
            self._loginstate.state_host.save_state("last_error_data", content)
            raise ValueError(
                'No file information in response (dump saved to state "last_error_data")'
            )
        files2 = [reformat_file_entry(fe, study_name) for fe in files]
        return files2

    def login_request(self, username: str, password: str, totp: str) -> DmpResponse:
        """
        Request a new login from the server
        :param username: The user name
        :param password: The password
        :param totp: The authentication code
        :return: On success: a DmpResponse with the user info and cookie set
        """
        query = read_text_resource("dmp_login.graphql")
        variables = {
            "username": username,
            "password": password,
            "totp":     totp,
        }
        # print(f'VARS = "{json.dumps(variables)}"')
        response = self.graphql_request(query, variables, False)
        # print(f'DEBUG: response content was: {response.jsontext}')
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        content: dict = json.loads(response.jsontext)
        data = safe_dict_get(content, "data")
        user = safe_dict_get(data, "login")
        if user is None:
            raise ValueError(f"Login failed")
        cookies = response.cookies_as_dict()
        if "connect.sid" not in cookies:
            raise ValueError(f"Login request did not return a login token / cookie")
        retval = DmpResponse(user, response.status, cookies)
        return retval

    # TODO: remove this backward compatibility stub
    @property
    def login_state(self) -> DmpLoginState:
        """
        Return the login state persistence handler
        """
        return self._loginstate

    pass
