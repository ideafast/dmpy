
from typing import List, Any, Dict, Optional
from .dmp_utils import safe_dict_get, safe_list_get
from datetime import datetime, timedelta, timezone, tzinfo


class DmpUserInfo:
    def __init__(self, raw: Dict[str, Any]):
        self._username = safe_dict_get(raw, 'username')
        self._firstname = safe_dict_get(raw, 'firstname')
        self._lastname = safe_dict_get(raw, 'lastname')
        self._email = safe_dict_get(raw, 'email')
        created = safe_dict_get(raw, 'createdAt')
        if created is None or created == 0:
            self._created = None
        else:
            created = datetime.fromtimestamp(created*0.001, tz=timezone.utc)
            self._created = created.isoformat(' ', 'seconds')
        expires = safe_dict_get(raw, 'expiredAt')
        if expires is None or expires == 0:
            self._expires = None
        else:
            expires = datetime.fromtimestamp(expires*0.001, tz=timezone.utc)
            self._expires = expires.isoformat(' ', 'seconds')
        access = safe_dict_get(raw, 'access')
        studies = safe_dict_get(access, 'studies')
        if studies is None:
            self._studies = None
        else:
            sd = dict()
            for d in studies:
                if d is not None:
                    study_id = safe_dict_get(d, 'id')
                    name = safe_dict_get(d, 'name')
                    if study_id is not None:
                        sd[study_id] = name or ''
            self._studies = sd
        pass

    @property
    def studies(self) -> Optional[Dict[str, str]]:
        return self._studies

    def matching_study_ids(self, prefix: str) -> List[str]:
        """
        Find full study ids matching the prefix. Returns an
        empty list if no matches are found
        """
        lst = []
        prefix = (prefix or '').lower()
        studies = self.studies
        if studies is not None:
            for sid, snm in studies.items():
                if sid.lower().startswith(prefix):
                    lst.append(sid)
        return lst

    def get_study_map(self) -> Optional[Dict[str, str]]:
        """
        Return a dictionary that maps available study IDs to study names.
        Returns None if there is no study information available (not logged in)
        """
        studies = self.studies
        if studies is not None:
            return {sid: snm for sid, snm in studies.items()}


    @property
    def expires(self) -> Optional[str]:
        return self._expires

    @property
    def created(self) -> Optional[str]:
        return self._created

    @property
    def email(self) -> Optional[str]:
        return self._email

    @property
    def lastname(self) -> Optional[str]:
        return self._lastname

    @property
    def firstname(self) -> Optional[str]:
        return self._firstname

    @property
    def username(self) -> Optional[str]:
        return self._username

    pass

