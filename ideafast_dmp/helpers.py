import json
from dataclasses import dataclass
from typing import Dict


@dataclass
class FileUploadPayload:
    """The payload required to upload a file"""

    studyID: str
    path: int
    patientID: str
    deviceID: str
    startWear: int
    endWear: int

    def dump_variables(self) -> Dict:
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
