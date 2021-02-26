import os
from pathlib import Path
from typing import Any, Dict, List

from .core.connection import DmpConnection
from .core.payloads import FileUploadPayload

USERNAME = os.environ.get("USERNAME", None)
PASSWORD = os.environ.get("PASSWORD", None)
CODE = os.environ.get("CODE", None)
# TODO: for future
API_TOKEN = os.environ.get("API_TOKEN", None)


class Dmpy:
    @staticmethod
    def auth() -> None:
        """??"""
        if None in [USERNAME, PASSWORD, CODE]:
            raise Exception("SECRETS")

        with DmpConnection("dmpapp") as dc:
            response = dc.login_request(USERNAME, PASSWORD, CODE)
            info = response.content
            dc.login_state.change_user(
                USERNAME,
                {"cookie": response.cookies["connect.sid"], "expiration": response.cookies["expiration"]},
                info
            )

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
        # Note: as requests is used upload is static at the moment
        with DmpConnection("dmpapp") as dc:
            response = dc.upload(payload)
        return response


def main():
    idf_dmpy = Dmpy()
    studyID = "a4080599-f721-47dc-8642-091297d6531b"
    path = Path("/Users/guanyu/Downloads/I7N3G6G-MMM7N3G6G-20200704-20200741.png")
    partientID = "I7N3G6G"
    deviceID = "MMM7N3G6G"
    startWear = 1593817200000
    endWear = 1595286000000
    payload = FileUploadPayload(studyID, path, partientID, deviceID, startWear, endWear)
    idf_dmpy.auth()
    response = idf_dmpy.upload(payload)
    print(response)
