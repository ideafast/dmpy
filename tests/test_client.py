import pytest
import logging
import os

from datetime import datetime
from unittest.mock import MagicMock, patch

from dmpy.client import Dmpy
from dmpy.core.payloads import FileUploadPayload


def test_secrets_set_default(mock_settings_env_vars) -> None:
    result = Dmpy().last_created

    assert result == 123456


def test_access_token_valid(mock_settings_env_vars) -> None:
    dmpy = Dmpy()

    dmpy.last_created = int(datetime.utcnow().timestamp())  # act

    with patch("requests.get"):
        result = dmpy.get_access_token()
        assert result == "FAKE_TOKEN_1234"


def test_access_token_expired(mock_settings_env_vars) -> None:
    new_token = "NEW_TOKEN"
    response = MagicMock(
        json=lambda: {"data": {"issueAccessToken": {"accessToken": new_token}}}
    )

    with patch("requests.post", return_value=response):
        result = Dmpy().get_access_token()  # act

        assert result == new_token
        assert os.getenv("DMP_ACCESS_TOKEN_GEN_TIME") != 123456


def test_access_token_response_http_error_thrown(
    caplog, mock_settings_env_vars
) -> None:
    response = MagicMock()
    response.raise_for_status.side_effect = Exception("TEST_EXCEPTION")

    with patch("requests.post", return_value=response), caplog.at_level(logging.ERROR):
        result = Dmpy().get_access_token()

        assert result == os.getenv("DMP_ACCESS_TOKEN")
        assert "TEST_EXCEPTION" in caplog.text


def test_access_token_response_error_thrown(
    caplog, mock_settings_env_vars, mock_dmp_token_response_error
) -> None:
    response = MagicMock()
    response.json.return_value = mock_dmp_token_response_error

    with patch("requests.post", return_value=response), caplog.at_level(logging.ERROR):
        result = Dmpy().get_access_token()

        assert result == os.getenv("DMP_ACCESS_TOKEN")
        assert "AUTH_ERROR" in caplog.text


def test_upload_success(mock_settings_env_vars, upload_payload) -> None:
    response = MagicMock(json=lambda: {})

    with patch("requests.post", return_value=response):
        result = Dmpy().upload(upload_payload)

        assert result == True


def test_upload_response_error(
    mock_settings_env_vars, mock_dmp_upload_response_error, upload_payload, caplog
) -> None:
    dmpy = Dmpy()

    # Ensures no new token is generated, skipping token's POST auth
    dmpy.last_created = int(datetime.utcnow().timestamp())

    response = MagicMock(json=lambda: mock_dmp_upload_response_error)

    with patch("requests.post", return_value=response), caplog.at_level(logging.ERROR):
        result = dmpy.upload(upload_payload)

        assert result == False
        assert "UPLOAD_ERROR" in caplog.text


def test_checksum_success(fake_file) -> None:
    result = Dmpy.checksum(fake_file)

    assert result == "a2dee47ba6268925da97750ab742baf67f02e2fb54ce23d499fb66a5b0222903"
