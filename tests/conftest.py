import pytest
import json
import os

from pathlib import Path
from unittest.mock import patch
from typing import Any, Generator

from dmpy.core.payloads import FileUploadPayload

folder = Path(__file__).parent


def read_json(filepath: Path) -> Any:
    with open(filepath, "r") as f:
        data = f.read()
    return json.loads(data)


@pytest.fixture(autouse=True)
def mock_settings_env_vars() -> Generator:
    getenv = {
        "DMP_STUDY_ID": "uuid-u-u-u-id",
        "DMP_URL": "https://fakeurl.com/graphql",
        "DMP_PUBLIC_KEY": "-----BEGIN PUBLIC KEY-----\\nABC123==\\n-----END PUBLIC KEY-----\\n",
        "DMP_SIGNATURE": "1234/56789",
        "DMP_ACCESS_TOKEN": "FAKE_TOKEN_1234",
        "DMP_ACCESS_TOKEN_GEN_TIME": "123456",
    }
    with patch.dict(os.environ, getenv):
        yield


@pytest.fixture(scope="function")
def upload_payload(fake_file):
    yield FileUploadPayload(
        Path(fake_file), "P-123456", "D-123456", 0, 0, "hash_id", "study_id"
    )

@pytest.fixture(scope="function")
def fake_file(tmp_path):
    fake_file = tmp_path / "filename.zip"
    fake_file.write_text("example content")
    yield fake_file


@pytest.fixture(scope="function")
def mock_dmp_token_response_error() -> dict:
    return read_json(Path(f"{folder}/data/token_response_error.json"))


@pytest.fixture(scope="function")
def mock_dmp_upload_response_error() -> dict:
    return read_json(Path(f"{folder}/data/upload_response_error.json"))