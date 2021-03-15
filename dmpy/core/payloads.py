import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import os

from .utils import read_text_resource


@dataclass
class FileUploadPayload:
    """The payload required to upload a file"""

    path: Path
    patient_id: str
    device_id: str
    start_wear: int
    end_wear: int
    content_hash: str
    # Default value used from .env or can be overridden
    # by assigning data to this varaible on class creation.
    study_id: str = os.getenv("DMP_STUDY_ID")

    def variables(self) -> Dict:
        """Dumps variables in a format suitable for DMP API,
        i.e. does not include file path."""
        return {
            "studyId": self.study_id,
            "description": json.dumps(
                {
                    "participantId": self.patient_id,
                    "deviceId": self.device_id,
                    "startDate": self.start_wear,
                    "endDate": self.end_wear,
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
