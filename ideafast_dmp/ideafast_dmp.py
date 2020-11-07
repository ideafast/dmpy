import os
from pathlib import Path
from typing import Any, Dict, List

from ideafast_dmp.dmp_connection import DmpConnection
from ideafast_dmp.helpers import FileUploadPayload

USERNAME = os.environ.get("USERNAME", None)
PASSWORD = os.environ.get("PASSWORD", None)
CODE = os.environ.get("CODE", None)
# TODO: for future
API_TOKEN = os.environ.get("API_TOKEN", None)


class ideafast_dmp:
    @staticmethod
    def auth() -> None:
        """??"""
        if None in [USERNAME, PASSWORD, CODE]:
            raise Exception("SECRETS")

        with DmpConnection("dmpapp") as dc:
            response = dc.login_request(USERNAME, PASSWORD, CODE)
            info = response.content
            cookie = response.cookies["connect.sid"]
            dc.login_state.change_user(USERNAME, cookie, info)

    def file_list(self, study_id: str) -> List[Dict[str, Any]]:
        """Get list of current files for study on DMP."""
        with DmpConnection("dmpapp") as dc:
            # NOTE: checks if log in is present and does NOT check if valid...
            if not dc.is_logged_in:
                raise Exception("Please log in.")
            # TODO: validation here?
            return dc.study_files_request(study_id)

    # TODO: we should have helper methods to validate DeviceID/PatientID, etc

    def upload(self, payload: FileUploadPayload) -> str:
        """Upload a single file to the DMP."""
        response = None
        with DmpConnection("dmpapp") as dc:
            # TODO: we will need to pass a lot more details ...
            # possibly use a dataclass to store/access data being sent?
            response = dc.upload(payload)
        return response or {}


def main():
    idf_dmpy = ideafast_dmp()
    study_id = "f4d96235-4c62-4910-a182-73836554036c"
    path = Path("/Users/jawrainey/code/ideafast/ideafast-dmp/example.png")
    partientID = "K9J9J9J"
    deviceID = "MMM9J9J9J"
    startWear = 1593817200000
    endWear = 1595286000000
    payload = FileUploadPayload(study_id, path, partientID, deviceID, startWear, endWear)
    response = idf_dmpy.upload(payload)
    print(response)
