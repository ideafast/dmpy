import hashlib
import json
from datetime import datetime
from pathlib import Path

import requests
from dotenv import get_key, load_dotenv, set_key
from requests_toolbelt.multipart.encoder import (
    MultipartEncoder,
    MultipartEncoderMonitor,
)
from tqdm import tqdm

from .core.payloads import FileUploadPayload
from .core.utils import read_text_resource


class Dmpy:
    def __init__(self):
        self.env = ".dmpy.env"
        self.url = get_key(self.env, "DMP_URL")
        load_dotenv(self.env)

    def access_token(self) -> str:
        """Obtain (or refresh) an access token."""
        now = int(datetime.utcnow().timestamp())
        last_created = int(get_key(self.env, "DMP_ACCESS_TOKEN_GEN_TIME"))
        # Refresh the token every 2 hours, i.e., below 200 minute limit.
        token_expired = (last_created + 60 * (60 * 2)) <= (now)

        if token_expired:
            request = {
                "query": read_text_resource("token.graphql"),
                "variables": {
                    "pubkey": get_key(self.env, "DMP_PUBLIC_KEY"),
                    "signature": get_key(self.env, "DMP_SIGNATURE"),
                },
            }

            response = requests.post(self.url, json=request)
            access_token = response.json()["data"]["issueAccessToken"]["accessToken"]

            set_key(self.env, "DMP_ACCESS_TOKEN", access_token)
            set_key(self.env, "DMP_ACCESS_TOKEN_GEN_TIME", str(now))
        return get_key(self.env, "DMP_ACCESS_TOKEN")

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

        print(f"Payload: {encoder}\n")

        with tqdm(total=encoder.len, unit="B", unit_scale=1, unit_divisor=1024) as bar:
            monitor = MultipartEncoderMonitor(
                encoder, lambda _monitor: bar.update(_monitor.bytes_read - bar.n)
            )

            headers = {
                "Content-Type": monitor.content_type,
                "Authorization": self.access_token(),
            }

            try:
                response = requests.post(
                    self.url, data=monitor, headers=headers, timeout=10
                )
                print(f"\nResponse: {response.json()}\n")
                return True
            except requests.exceptions.Timeout as err:
                print(f"Timeout occurred: {err}")
                return False
            except Exception as err:
                print(f"Unknown error: {err}")
                return False

    @staticmethod
    def checksum(path: Path, hash_factory=hashlib.sha256) -> str:
        """
        Create a hash from a file's contents at a given path.
        :param path: location
        :param hash_factory: allows overriding hash used (e.g., SHA256, blake, etc)
        :return a hex checksum of the file's contents
        """
        with open(path, "rb") as f:
            file_hash = hash_factory()
            while chunk := f.read(128 * file_hash.block_size):
                file_hash.update(chunk)
        return file_hash.hexdigest()
