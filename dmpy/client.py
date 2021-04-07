import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import os
import requests
from requests_toolbelt.multipart.encoder import (
    MultipartEncoder,
    MultipartEncoderMonitor,
)

from .core.payloads import FileUploadPayload
from .core.utils import read_text_resource

log = logging.getLogger(__name__)


class Dmpy:
    def __init__(self):
        self.url = os.getenv("DMP_URL")
        self.pubkey = os.getenv("DMP_PUBLIC_KEY")
        self.signature = os.getenv("DMP_SIGNATURE")
        # Store these in memory rather than file
        self.access_token = os.getenv("DMP_ACCESS_TOKEN", "")
        self.last_created = int(os.getenv("DMP_ACCESS_TOKEN_GEN_TIME", 0))

    def get_access_token(self) -> str:
        """Obtain (or refresh) an access token."""
        now = int(datetime.utcnow().timestamp())
        # Refresh the token every 2 hours, i.e., below 200 minute limit.
        token_expired = (self.last_created + 60 * (60 * 2)) <= now

        if token_expired:
            request = {
                "query": read_text_resource("token.graphql"),
                "variables": {
                    "pubkey": self.pubkey,
                    "signature": self.signature,
                },
            }

            try:
                response = requests.post(self.url, json=request)
                response.raise_for_status()
                json_response = response.json()

                # DMP does not use HTTP status_codes and instead returns
                # 200 and a list of errors when one occurs.
                if "errors" in json_response:
                    log.error(f"Response was: {json_response}")
                    raise Exception("AUTH_ERROR")

                access_token = json_response["data"]["issueAccessToken"]["accessToken"]

                self.access_token = access_token
                os.environ["DMP_ACCESS_TOKEN"] = access_token
                os.environ["DMP_ACCESS_TOKEN_GEN_TIME"] = str(now)
            except Exception:
                log.error("Exception:", exc_info=True)
        return self.access_token

    def upload(self, payload: FileUploadPayload) -> bool:
        """
        Upload a single file to the DMP.
        :param payload: The validated FileUploadPayload to send.
        :return: True/False depending on upload success
        """
        encoder = MultipartEncoder(
            {
                "operations": payload.operations(),
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

        log.debug(f"Payload: {encoder}\n")

        # Store the percentage of progress. Used because bytes sent may be
        # within a specific percentage, e.g., 90.07, 90.10, 90.14, etc.
        # We only want to print this percentage once.
        percent_uploaded = 0

        def log_progress(monitor: MultipartEncoderMonitor):
            """Logs data transfer progress when 10% of file uploaded."""
            # Gain access to the variable in the outter scope
            nonlocal percent_uploaded

            bytes_sent = monitor.bytes_read
            upload_percent = int(bytes_sent / monitor.len * 100)
            # httplib's default blocksize.
            # cannot be easily overriden: https://github.com/requests/toolbelt/issues/75
            blocksize = 8192

            if (
                # 0%, i.e., first bytes sent
                bytes_sent == blocksize
                # Only print when first bytes sent (i.e., it has started) OR
                # when the first bytes of the next 10% are uploaded, e.g.,
                or upload_percent % 10 == 0
                and percent_uploaded != upload_percent
            ):
                log.debug(f"{upload_percent}% Uploaded | {bytes_sent} Bytes Sent")
                percent_uploaded = upload_percent

        monitor = MultipartEncoderMonitor(encoder, log_progress)

        headers = {
            "Content-Type": monitor.content_type,
            "Authorization": self.get_access_token(),
        }

        try:
            # Seconds to wait to establish connection with server
            connect = 4
            # Wait at most 5 minutes for server response between bytes sent
            # required as server timeout after uploading large files (>2GB)
            read = 60 * 5 + 2
            response = requests.post(
                self.url,
                data=monitor,
                headers=headers,
                timeout=(connect, read),
                stream=True,
            )
            response.raise_for_status()

            json_response = response.json()

            if "errors" in json_response:
                log.error(f"Response was: {json_response}")
                raise Exception("UPLOAD_ERROR")

            log.info(f"Uploaded {percent_uploaded}%")
            log.debug(f"Response: {json_response}")

            return True
        except Exception:
            log.error("Exception:", exc_info=True)
        return False

    @staticmethod
    def checksum(path: Path, hash_factory=hashlib.sha256) -> str:
        """
        Create a hash from a file's contents at a given path.
        :param path: location
        :param hash_factory: allows overriding hash used (e.g., SHA256, blake, etc)
        :return a hex checksum of the file's contents
        """
        log.info("Creating checksum")
        with open(path, "rb") as f:
            file_hash = hash_factory()
            while chunk := f.read(128 * file_hash.block_size):
                file_hash.update(chunk)
        digest = file_hash.hexdigest()
        log.info(f"Checksum created: {digest}")
        return digest
