import json
from typing import Any, Dict, List

from ideafast_platform_access.dmp_connection import DmpConnection

class ideafast_dmp:
    @staticmethod
    def auth(username, password, code) -> None:
        with DmpConnection('dmpapp') as dc:
            response = dc.login_request(username, password, code)
            info = response.content
            cookie = response.cookies['connect.sid']
            dc.login_state.change_user(username, cookie, info)


    def download_file_list(self, study_id: str) -> List[Dict[str, Any]]:
        """Get list of current files for study on DMP."""
        with DmpConnection('dmpapp') as dc:
            # NOTE: checks if log in is present and does NOT check if valid...
            if not dc.is_logged_in:
                raise Error('Please log in.')
            # TODO: validation here?
            return dc.study_files_request(study_id)
    

    def upload(self, study_id: str, filename: str) -> str:
        """Upload a single file to the DMP."""
        pass