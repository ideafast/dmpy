import os
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from dmpy.client import Dmpy


def test_secrets_set_default(mock_settings_env_vars) -> None:
    assert Dmpy().last_created == 123456  # act


def test_access_token_valid(mock_settings_env_vars) -> None:
    dmpy = Dmpy()

    dmpy.last_created = int(datetime.utcnow().timestamp())  # act

    with patch("requests.get"):
        assert dmpy.get_access_token() == "FAKE_TOKEN_1234"


def test_access_token_expired(mock_settings_env_vars) -> None:
    new_token = "NEW_TOKEN"
    response = MagicMock(
        json=lambda: {"data": {"issueAccessToken": {"accessToken": new_token}}}
    )

    with patch("requests.post", return_value=response):
        token = Dmpy().get_access_token()  # act

        assert token == new_token
        assert os.getenv("DMP_ACCESS_TOKEN_GEN_TIME") != 123456


def test_access_token_response_http_error_thrown(
    caplog, mock_settings_env_vars
) -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = Exception("TEST_EXCEPTION")

    with patch("requests.post", return_value=response), caplog.at_level(logging.ERROR):
        token = Dmpy().get_access_token()

        assert token == os.getenv("DMP_ACCESS_TOKEN")
        assert "TEST_EXCEPTION" in caplog.text


def test_access_token_response_error_thrown(
    caplog, mock_settings_env_vars, mock_dmp_token_error_response
) -> None:
    response = MagicMock()
    response.json.return_value = mock_dmp_token_error_response

    with patch("requests.post", return_value=response), caplog.at_level(logging.ERROR):
        token = Dmpy().get_access_token()

        assert token == os.getenv("DMP_ACCESS_TOKEN")
        assert "AUTH_ERROR" in caplog.text


def test_upload_success() -> None:
    pass


def test_upload_thrown() -> None:
    pass


def test_upload_response_error() -> None:

    pass


def test_checksum_success(tmp_path) -> None:
    path = tmp_path / "filename.zip"

    path.write_text("example content")
    result = Dmpy.checksum(path)

    assert result == "a2dee47ba6268925da97750ab742baf67f02e2fb54ce23d499fb66a5b0222903"