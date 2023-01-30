# interaction with the DMP server
from __future__ import annotations
import functools
import http.client
import json
import re
from http.cookies import Morsel, SimpleCookie
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from time import time as now
import os

from .payloads import FileUploadPayload
from .login_state import DmpLoginState
from .utils import read_text_resource, safe_dict_get, safe_list_get, stamp_to_text


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


class DmpConnection:
    """
    Represents a connection to the DMP server
    """

    def __init__(self, appname: str, server: str = None):
        """
        Create a connection to the DMP server. This object acts as its own "context manager",
        so use this constructor in a "with" block
        :param appname: The application name, used to locate the persisted login information
        :param server: The server name or None to use the default ('data.ideafast.eu')
        """
        if server is None:
            dmp_endpoint = os.getenv('DMP_ENDPOINT')
            if dmp_endpoint == 'production':
                server = "data.ideafast.eu"
            elif dmp_endpoint == 'staging':
                server = "staging.wp5.ideafast.eu"
            else:
                server = "staging.wp5.ideafast.eu"
        self._server = server
        self._conn = http.client.HTTPSConnection(self._server)
        self._loginstate = DmpLoginState(appname)
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
        return self._loginstate.is_logged_in

    def _check_expiration(func):
        @functools.wraps(func)
        def wrap(self, *args, **kwargs):
            auth_method = self._loginstate.auth_method
            if auth_method == 1:
                if self._loginstate.cookie is None:
                    raise Exception("no cookie info found")
                else:
                    expiration = self._loginstate.cookie["expiration"]
                    if float(expiration) < now():
                        raise Exception("Login session expired")
            elif auth_method == 2:
                if self._loginstate.access_token is None:
                    raise Exception("no access token info setup")
                else:
                    expiration = self._loginstate.access_token["expiration"]
                    if expiration < now():
                        self.refresh_token()
            return func(self, *args, **kwargs)
        return wrap

    def refresh_token(self):
        """
        Request a new access token using the public key and signature if previous one is expired.
        Once got the new access token, update it into login state and set the expiration time.
        """
        if self._loginstate.access_token is None:
            raise Exception("public key and signature required")
        query = read_text_resource("issue_token.graphql")
        public_key_path = self._loginstate.access_token["public_key_path"]
        signature_path = self._loginstate.access_token["signature_path"]
        with open(public_key_path, 'r') as public_key:
            with open(signature_path, 'r') as signature:
                variables = {"pubkey": public_key.read(), "signature": signature.read()}
                self._loginstate.set_auth_method(0)
                response = self.graphql_request(query, variables)
                if response.status != 200:
                    raise ValueError(f"Query was rejected by server (status {response.status})")
                content: dict = json.loads(response.jsontext)

                if "errors" not in content:
                    data = safe_dict_get(content, "data")
                    issued_token = safe_dict_get(data, "issueAccessToken")
                    token = safe_dict_get(issued_token, "accessToken")
                    if token is not None:
                        self._loginstate.refresh_token(token)
                    else:
                        print(content)
                else:
                    raise Exception(content["errors"])

    def graphql_request(
        self, query: str, variables: any
    ) -> DmpGqlResponse:
        """
        Initiate a request to the DMP server's GraphQL query endpoint
        :param query: The GraphQL query text
        :param variables: The query parameters
        :param auth_method: (default 1) Can only be 0, 1 or 2.
        If 0, this should be for login or token refresh request
        if 1, use cookie as authentication. If 2,use access token.
        :return: The full JSON text from the response
        """
        headers = {
            "Content-Type": "application/json",
        }
        if self._loginstate.auth_method == 1:
            if self._loginstate.cookie is None:
                raise Exception("You are not logged in")
            headers["Cookie"] = "connect.sid=" + self._loginstate.cookie["cookie"]
        elif self._loginstate.auth_method == 2:
            if self._loginstate.access_token is None:
                raise Exception("no access token info setup")
            headers["Authorization"] = self._loginstate.access_token["token"]
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

    @_check_expiration
    def download_file(
        self,
        file_id: str,
        dest: Union[Path, str],
        progress: Optional[Callable[[int], None]] = None,
    ) -> int:
        """
        Download and overwrite a single file from the server to the given local destination file
        :param file_id: The full file id of the file to download
        :param dest: The destination file name. This must be an absolute path.
        :param progress: An optional progress callback. If not None, this is called repeatedly with the
        number of bytes downloaded so far
        :return: The HTTP status code (200 on success)
        """
        dest = Path(dest)
        if not dest.is_absolute():
            raise ValueError("Expecting an absolute path as destination file")
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
        headers = {}

        if self._loginstate.auth_method == 1:
            if self._loginstate.cookie is None:
                raise Exception("You are not logged in")
            headers["Cookie"] = "connect.sid=" + self._loginstate.cookie["cookie"]
        elif self._loginstate.auth_method == 2:
            if self._loginstate.access_token is None:
                raise Exception("no access token info setup")
            headers["Authorization"] = self._loginstate.access_token["token"]

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

    @_check_expiration
    def upload(self, payload: FileUploadPayload) -> Dict:
        """
        Upload a single file to the DMP.
        :param payload: The validated FileUploadPayload to send.
        :return: A dictionary containing
        """
        import requests  # noqa
        from requests_toolbelt.multipart.encoder import MultipartEncoder  # noqa

        # TODO: we could do payload.validate() that raises error if input is invalid?

        multipart_data = MultipartEncoder(
            {
                "operations": payload.operations(),
                # TODO: determine if this can be removed/simplified from WP5?
                # Note: unclear how uploading many files would work,
                # could 'map' be removed and next para be 'file' instead?
                "map": json.dumps({"fileName": ["variables.file"]}),
                "fileName": (
                    payload.path.name,
                    open(
                        payload.path,
                        "rb",
                    ),
                    "application/octet-stream",
                ),
            }
        )

        headers = {
            "Content-Type": multipart_data.content_type
        }
        if self._loginstate.auth_method == 1:
            if self._loginstate.cookie is None:
                raise Exception("You are not logged in")
            headers["Cookie"] = "connect.sid=" + self._loginstate.cookie["cookie"]
        elif self._loginstate.auth_method == 2:
            if self._loginstate.access_token is None:
                raise Exception("no access token info setup")
            headers["Authorization"] = self._loginstate.access_token["token"]
        # TODO: below works with the use of http client
        # self._conn.request("POST", "/graphql", multipart_data, headers)
        # res: http.client.HTTPResponse = self._conn.getresponse()
        # data = res.read()
        # print(data, res.status, data.decode("utf-8"))

        url = "https://data.ideafast.eu/graphql"
        response = requests.post(url, data=multipart_data, headers=headers)
        # TODO: error handling ...
        return response.json()

    @_check_expiration
    def user_info_request(self) -> DmpResponse:
        """
        Request the information record for the "currently logged in user" from
        the server. Raises an exception if there is no currently logged in user.
        Raises an exception if the current user information is no longer considered
        valid by the server.
        :return: A response object. The content is the user info object
        """
        query = read_text_resource("whoami.graphql")
        response = self.graphql_request(query, None)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")

        content: dict = json.loads(response.jsontext)
        data = safe_dict_get(content, "data")
        user = safe_dict_get(data, "whoAmI")
        retval = DmpResponse(user, response.status, response.cookies_as_dict())
        return retval

    @_check_expiration
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
                "fileId": fe["id"],
                "fileName": fe.get("fileName"),
                "fileSize": fe["fileSize"],
                # 'description': description,
                "participantId": safe_dict_get(description, "participantId"),
                "deviceKind": device_kind,
                "deviceId": device_id,
                "timeStart": stamp_to_text(start_stamp),
                "timeEnd": stamp_to_text(end_stamp),
                "timeUpload": stamp_to_text(utt),
                "stampStart": start_stamp,
                "stampEnd": end_stamp,
                "stampUpload": utt,
                "uploadedBy": fe.get("uploadedBy"),
                "studyId": fe.get("studyId"),
                "studyName": studyname,
            }
            return ret

        query = read_text_resource("study_files.graphql")
        info = self._loginstate.info
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
            self._loginstate.state_host.save_state("last_error_data", content)
            raise ValueError(
                'No file information in response (dump saved to state "last_error_data")'
            )
        files2 = [reformat_file_entry(fe, study_name) for fe in files]
        return files2

    @_check_expiration
    def register_pubkey(self, public_key: str, signature: str, user_id: str):
        query = read_text_resource("register_pubkeys.graphql")
        variables = {
            "pubkey": public_key,
            "signature": signature,
            "associatedUserId": user_id
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    def login_request(self, username: str, password: str, totp: str) -> DmpResponse:
        """
        Request a new login from the server
        :param username: The user name
        :param password: The password
        :param totp: The authentication code
        :return: On success: a DmpResponse with the user info and cookie set
        """
        query = read_text_resource("login.graphql")

        variables = {
            "username": username,
            "password": password,
            "totp": totp,
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        expiration = now() + 3600 * 2
        content: dict = json.loads(response.jsontext)
        data = safe_dict_get(content, "data")
        user = safe_dict_get(data, "login")

        if user is None:
            raise ValueError("Login failed")
        cookies = response.cookies_as_dict()

        if "connect.sid" not in cookies:
            raise ValueError("Login request did not return a login cookie")

        cookies["expiration"] = str(expiration)

        retval = DmpResponse(user, response.status, cookies)
        return retval

    @property
    def login_state(self) -> DmpLoginState:
        """
        Return the login state persistence handler
        """
        return self._loginstate

    pass

    @_check_expiration
    def create_data_curation(self, file_id: str, study_id: str, version: str, tag: str = None):
        query = read_text_resource("create_data_curation.graphql")
        variables = {
            "file": file_id,
            "studyId": study_id,
            "version": version
        }
        if tag:
            variables["tag"] = tag
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def create_field_curation(self, file_list: List[str], study_id: str, version: str, tag: str = None):
        query = read_text_resource("create_field_curation.graphql")
        variables = {
            "file": file_list,
            "studyId": study_id,
            "dataVersionId": version
        }
        if tag:
            variables["tag"] = tag
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def create_project(self, study_id: str, project_name: str,):
        query = read_text_resource("create_project.graphql")
        variables = {
            "studyId": study_id,
            "projectName": project_name
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def create_query(self, study_id: str, query_string: str, user_id: str, project_id: str):
        query = read_text_resource("create_query.graphql")
        data_query = {
            "queryString": query_string,
            "userId": user_id,
            "studyId": study_id,
            "projectId": project_id
        }
        variables = {
            "query": data_query
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def create_query_curation(self, query_ids: List[str], study_id: str, project_id: str, version: str = None):
        query = read_text_resource("create_query_curation.graphql")
        variables = {
            "queryId": query_ids,
            "studyId": study_id,
            "projectId": project_id,
            "version": version
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def get_study_fields(self, study_id: str, field_tree_id: str = None):
        query = read_text_resource("get_study_fields.graphql")
        variables = {
            "studyId": study_id
        }

        if field_tree_id:
            variables["fieldTreeId"] = field_tree_id
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def get_full_study(self, study_id: str):
        query = read_text_resource("get_study.graphql")
        variables = {
            "studyId": study_id
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def get_query_by_id(self, query_id: str):
        query = read_text_resource("get_query_by_id.graphql")
        variables = {
            "queryId": query_id
        }
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status})")
        return json.loads(response.jsontext)

    @_check_expiration
    def execute_graphql(self, query_file_name, variables):
        query = read_text_resource(query_file_name)
        response = self.graphql_request(query, variables)
        if response.status != 200:
            raise ValueError(f"Query was rejected by server (status {response.status}) : {response.jsontext}")
        return json.loads(response.jsontext)

