import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from .utils import read_text_resource


@dataclass
class FileUploadPayload:
    """The payload required to upload a file"""

    studyID: str
    path: Path
    patientID: str
    deviceID: str
    startWear: int
    endWear: int
    # TODO: add __post_init__ to validate properties?

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
                }
            ),
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