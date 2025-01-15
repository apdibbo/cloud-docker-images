"""This test file covers all tests for the read_config module."""

from unittest.mock import patch, mock_open
import pytest
from helper.data import User
from helper.errors import ErrorInConfig
from helper.read_config import get_token, get_config, validate_required_files, get_path

MOCK_CONFIG = """
---
users:
  - real_name: mock user
    github_name: mock_github
    slack_id: mock_slack
repos:
  organisation1:
    - repo1
    - repo2
  organisation2:
    - repo1
    - repo2
channel: mock_channel
"""

MOCK_USER = User(
    real_name="mock user", github_name="mock_github", slack_id="mock_slack"
)


def test_get_path_prod():
    """Test the production path is returned"""
    assert get_path() == "/usr/src/app/cloud_chatops/"


@patch("helper.read_config.os")
@patch("helper.read_config.sys")
def test_get_path_dev_linux(mock_sys, mock_os):
    """Test the development path is returned for a system using the HOME environment variable."""
    mock_sys.argv = ["dev.py"]
    mock_os.environ = {"HOME": "/home/mock"}
    assert get_path() == "/home/mock/dev_cloud_chatops/"


@patch("helper.read_config.os")
@patch("helper.read_config.sys")
def test_get_path_dev_windows(mock_sys, mock_os):
    """Test the development path is returned for a system using the HOMEPATH environment variable."""
    mock_sys.argv = ["dev.py"]
    mock_os.environ = {"HOMEPATH": "\\home\\mock"}
    assert get_path() == "\\home\\mock\\dev_cloud_chatops\\"


@patch("helper.read_config.os")
@patch("helper.read_config.sys")
def test_get_path_dev_fails(mock_sys, mock_os):
    """Test an error is raised if HOME or HOMEPATH can't be found in the environment."""
    mock_sys.argv = ["dev.py"]
    mock_os.environ = {}
    with pytest.raises(ErrorInConfig):
        get_path()


def test_get_token_fails():
    """Test that an error is raised if trying to access a value that doesn't exist."""
    with patch("builtins.open", mock_open(read_data="mock_token_1: mock_value_1")):
        with pytest.raises(KeyError):
            get_token("mock_token_2")


def test_get_token():
    """This test checks that a value is returned when the function is called with a specific token."""
    with patch("builtins.open", mock_open(read_data="mock_token_1: mock_value_1")):
        res = get_token("mock_token_1")

        assert res == "mock_value_1"


def test_get_config_users():
    """This test ensures that a list of User objects is returned from the config."""
    with patch("builtins.open", mock_open(read_data=MOCK_CONFIG)):
        res = get_config("users")
        assert res == [MOCK_USER]


def test_get_config_repos():
    """This test checks that a list is returned if a string list of repos is read with no comma at the end."""
    with patch("builtins.open", mock_open(read_data=MOCK_CONFIG)):
        res = get_config("repos")
        assert res == [
            "organisation1/repo1",
            "organisation1/repo2",
            "organisation2/repo1",
            "organisation2/repo2",
        ]


def test_get_config_channel():
    """Tests that the channel is returned from the config."""
    with patch("builtins.open", mock_open(read_data=MOCK_CONFIG)):
        res = get_config("channel")
        assert res == "mock_channel"


def test_get_config_fails():
    """This test checks that an error is raised when accessing a part of the config that doesn't exist."""
    with patch("builtins.open", mock_open(read_data=MOCK_CONFIG)):
        with pytest.raises(KeyError):
            get_config("unknown")


@patch("helper.read_config.get_config")
@patch("helper.read_config.get_token")
def test_validate_required_files(mock_get_token, mock_get_config):
    """Test the validate files function"""
    mock_get_token.side_effect = ["mock_bot", "mock_app", "mock_github"]
    mock_get_config.side_effect = [
        {"owner1": ["repo1"]},
        {"github1": "slack1"},
        "mock_channel",
    ]
    validate_required_files()


@patch("helper.read_config.get_config")
@patch("helper.read_config.get_token")
def test_validate_required_files_fail_repo(mock_get_token, mock_get_config):
    """Test the validate files function"""
    mock_get_token.side_effect = ["mock_bot", "mock_app", "mock_github"]
    mock_get_config.side_effect = [{}, {"github1": "slack1"}]
    with pytest.raises(ErrorInConfig):
        validate_required_files()


@patch("helper.read_config.get_config")
@patch("helper.read_config.get_token")
def test_validate_required_files_fail_token(mock_get_token, mock_get_config):
    """Test the validate files function"""
    mock_get_token.side_effect = ["", "mock_app", "mock_github"]
    mock_get_config.side_effect = [{"owner1": ["repo1"]}, {"github1": "slack1"}]
    with pytest.raises(ErrorInConfig):
        validate_required_files()


@patch("helper.read_config.get_config")
@patch("helper.read_config.get_token")
def test_validate_required_files_fail_users(mock_get_token, mock_get_config):
    """Test the validate files function"""
    mock_get_token.side_effect = ["mock_bot", "mock_app", "mock_github"]
    mock_get_config.side_effect = [{"owner1": ["repo1"]}, {}]
    with pytest.raises(ErrorInConfig):
        validate_required_files()


@patch("helper.read_config.get_config")
@patch("helper.read_config.get_token")
def test_validate_required_files_fail_channel(mock_get_token, mock_get_config):
    """Test the validate files function"""
    mock_get_token.side_effect = ["mock_bot", "mock_app", "mock_github"]
    mock_get_config.side_effect = [
        {"owner1": ["repo1"]},
        {"mock_github": "mock_user"},
        "",
    ]
    with pytest.raises(ErrorInConfig):
        validate_required_files()
