import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .utils import read_text_resource


@dataclass
class FileUploadPayload:
    """The payload required to upload a file"""

    # NOTE: These ideally mirror middleware naming
    # so we can more easily unpack a Record
    studyID: str
    path: Path
    patientID: str
    deviceID: str
    startWear: int
    endWear: int
    content_hash: str

    def variables(self) -> Dict:
        """Dumps variables in a format suitable for DMP API,
        i.e. does not include file path."""
        return {
            "studyId": self.studyID,
            "description": json.dumps(
                {
                    "participantId": self.patientID,
                    "deviceId": self.deviceID,
                    "startDate": self.startWear,
                    "endDate": self.endWear,
                },
            ),
            "hash": self.content_hash,
        }

    def operations(self) -> Dict:
        """Constructs the upload operations and query to send to the API."""
        return json.dumps(
            {
                "operationName": "uploadFile",
                "variables": self.variables(),
                "query": read_text_resource("upload.graphql").replace("\n", " "),
            }
        )
