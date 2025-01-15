"""Unit tests for events.py"""

from unittest.mock import patch, MagicMock
import pytest

from helper.data import User
from events import (
    run_global_reminder,
    run_personal_reminder,
    weekly_reminder,
    slash_prs,
    slash_find_host,
)

MOCK_USER = User(
    real_name="mock user", github_name="mock_github", slack_id="mock_slack"
)

# Disable for patching
# pylint: disable=R0917
# pylint: disable=R0913


@patch("events.sort_by")
@patch("events.WebClient")
@patch("events.get_token")
@patch("events.get_config")
@patch("events.FindPRs")
@patch("events.PRReminder")
def test_run_global_reminder(
    mock_pr_reminder,
    mock_find_prs,
    mock_get_config,
    mock_get_token,
    mock_web_client,
    mock_sort_by,
):
    """Test global reminder event"""
    mock_get_token.side_effect = ["mock_github", "mock_slack"]
    run_global_reminder("mock_channel")
    mock_find_prs.return_value.run.assert_called_once_with(
        repos=mock_get_config.return_value, token="mock_github"
    )
    mock_sort_by.assert_called_once_with(
        mock_find_prs.return_value.run.return_value, "created_at", False
    )
    mock_web_client.assert_called_once_with(token="mock_slack")
    mock_pr_reminder.assert_called_once_with(mock_web_client.return_value)
    mock_pr_reminder.return_value.run.assert_called_once_with(
        prs=mock_sort_by.return_value, channel="mock_channel"
    )
    mock_get_config.assert_called_once_with("repos")
    mock_get_token.assert_any_call("GITHUB_TOKEN")
    mock_get_token.assert_any_call("SLACK_BOT_TOKEN")

# Disable for patching
# pylint: disable=R0917
# pylint: disable=R0913


@patch("events.sort_by")
@patch("events.filter_by")
@patch("events.WebClient")
@patch("events.get_token")
@patch("events.get_config")
@patch("events.FindPRs")
@patch("events.PRReminder")
def test_run_personal_reminder(
    mock_pr_reminder,
    mock_find_prs,
    mock_get_config,
    mock_get_token,
    mock_web_client,
    mock_filter_by,
    mock_sort_by,
):
    """Test personal reminder event"""
    mock_get_token.side_effect = ["mock_github", "mock_slack"]
    mock_repos = {"mock_owner": ["mock_repo"]}
    mock_get_config.side_effect = [mock_repos]
    run_personal_reminder([MOCK_USER])
    mock_find_prs.return_value.run.assert_called_once_with(
        repos=mock_repos, token="mock_github"
    )
    mock_sort_by.assert_called_once_with(
        mock_find_prs.return_value.run.return_value, "created_at", False
    )
    mock_filter_by.assert_called_once_with(
        mock_sort_by.return_value, "author", "mock_github"
    )
    mock_get_config.assert_any_call("repos")
    mock_web_client.assert_called_once_with(token="mock_slack")
    mock_get_token.assert_any_call("SLACK_BOT_TOKEN")
    mock_get_token.assert_any_call("GITHUB_TOKEN")
    mock_pr_reminder.assert_called_once_with(mock_web_client.return_value)
    mock_pr_reminder.return_value.run.assert_called_once_with(
        prs=mock_filter_by.return_value,
        channel="mock_slack",
        message_no_prs=False,
    )


@patch("events.run_global_reminder")
@patch("events.run_personal_reminder")
@patch("events.get_config")
def test_weekly_reminder(mock_get_config, mock_personal, mock_global):
    """Test the correct jobs are run"""
    mock_get_config.side_effect = ["channel", [MOCK_USER]]
    weekly_reminder("global")
    mock_get_config.assert_any_call("channel")
    mock_global.assert_called_once_with("channel")

    weekly_reminder("personal")
    mock_get_config.assert_any_call("users")
    mock_personal.assert_called_once_with(users=[MOCK_USER], message_no_prs=False)


def test_weekly_reminder_fails():
    """Test the functions raises an error for an incorrect job."""
    with pytest.raises(ValueError):
        weekly_reminder("some_incorrect_value")


@patch("events.run_personal_reminder")
@patch("events.get_config")
def test_slash_prs_mine(mock_get_config, mock_run_personal):
    """Test the function works when users choose "mine" """
    mock_get_config.return_value = [MOCK_USER]
    mock_respond = MagicMock()
    mock_command = {"user_id": "mock_slack", "text": "mine"}
    mock_ack = MagicMock()
    slash_prs(mock_ack, mock_respond, mock_command)
    mock_ack.assert_called_once_with()
    mock_get_config.assert_called_once_with("users")
    mock_respond.assert_any_call("Gathering the PRs...")
    mock_respond.assert_any_call("Check out your DMs.")
    mock_run_personal.assert_called_once_with([MOCK_USER], message_no_prs=True)


@patch("events.run_global_reminder")
@patch("events.get_config")
def test_slash_prs_all(mock_get_config, mock_run_global):
    """Test the function works when users choose all"""
    mock_get_config.return_value = [MOCK_USER]
    mock_respond = MagicMock()
    mock_command = {"user_id": "mock_slack", "text": "all"}
    mock_ack = MagicMock()
    slash_prs(mock_ack, mock_respond, mock_command)
    mock_ack.assert_called_once_with()
    mock_get_config.assert_called_once_with("users")
    mock_respond.assert_any_call("Gathering the PRs...")
    mock_respond.assert_any_call("Check out your DMs.")
    mock_run_global.assert_called_once_with("mock_slack")


@patch("events.get_config")
def test_slash_prs_fail(mock_get_config):
    """Test the function fails if no option is given"""
    mock_get_config.return_value = [MOCK_USER]
    mock_respond = MagicMock()
    mock_command = {"user_id": "mock_slack", "text": ""}
    mock_ack = MagicMock()
    slash_prs(mock_ack, mock_respond, mock_command)
    mock_ack.assert_called_once_with()
    mock_get_config.assert_called_once_with("users")
    mock_respond.assert_any_call(
        "Please provide the correct argument: 'mine' or 'all'."
    )


@patch("events.get_config")
def test_slash_prs_no_user(mock_get_config):
    """Test the function fails if the user is not found in the config file"""
    mock_get_config.return_value = [MOCK_USER]
    mock_respond = MagicMock()
    mock_command = {"user_id": "non_existent_user", "text": ""}
    mock_ack = MagicMock()
    slash_prs(mock_ack, mock_respond, mock_command)
    mock_ack.assert_called_once_with()
    mock_get_config.assert_called_once_with("users")
    mock_respond.assert_any_call(
        "Could not find your Slack ID non_existent_user in the user map. "
        "Please contact the service maintainer to fix this."
    )


@patch("events.os")
def test_slash_find_host(mock_os):
    """Test that the environment variable is retrieved and responded."""
    mock_ack = MagicMock()
    mock_respond = MagicMock()
    slash_find_host(mock_ack, mock_respond)
    mock_ack.assert_called_once_with()
    mock_os.environ.get.assert_called_once_with("HOST_IP")
    mock_respond.assert_called_once_with(
        f"The host IP of this node is: {mock_os.environ.get.return_value}"
    )
