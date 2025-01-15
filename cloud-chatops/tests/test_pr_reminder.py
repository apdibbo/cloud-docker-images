"""Tests for pr_reminder.py"""

from dataclasses import replace
from datetime import datetime
from unittest.mock import patch, NonCallableMock, MagicMock
import pytest
from slack_reminder_api.pr_reminder import PRReminder
from helper.data import PR, Message, User


@pytest.fixture(name="instance", scope="function")
def instance_fixture():
    """Fixture for class instance."""
    return PRReminder(NonCallableMock())


# pylint: disable=R0801


MOCK_PR = PR(
    title="mock_title #1",
    author="mock_github",
    url="https://api.github.com/repos/mock_owner/mock_repo/pulls",
    stale=True,
    draft=True,
    labels=["mock_label"],
    repository="mock_repo",
    created_at=datetime.strptime("2024-11-15T07:33:56Z", "%Y-%m-%dT%H:%M:%SZ"),
)

MOCK_PR_2 = PR(
    title="mock_title #1",
    author="mock_github_2",
    url="https://api.github.com/repos/mock_owner/mock_repo/pulls",
    stale=True,
    draft=True,
    labels=["mock_label"],
    repository="mock_repo",
    created_at=datetime.strptime("2024-11-15T07:33:56Z", "%Y-%m-%dT%H:%M:%SZ"),
)

MOCK_USER = User(
    real_name="mock user", github_name="mock_github", slack_id="mock_slack"
)


def test_get_reactions(instance):
    """Test reactions are returned."""
    res = instance.get_reactions(MOCK_PR)
    assert res == ["alarm_clock", "building_construction"]


def test_get_reactions_none(instance):
    """Test no reactions are returned."""
    mock_pr = replace(MOCK_PR, draft=False, stale=False)
    res = instance.get_reactions(mock_pr)
    assert not res


@patch("slack_reminder_api.pr_reminder.get_config")
def test_make_string(mock_get_config, instance):
    """Test the right string is returned."""
    mock_get_config.return_value = [MOCK_USER]
    res = instance.make_string(MOCK_PR)
    mock_get_config.assert_called_once_with("users")
    expected = (
        f"*This PR is older than 30 days. Consider closing it:*"
        f"\nPull Request: <{MOCK_PR.url}|{MOCK_PR.title}>\nAuthor: mock user"
    )
    assert res == expected


@patch("slack_reminder_api.pr_reminder.get_config")
def test_make_string_fails(mock_get_config, instance):
    """Test the github name is used if slack name can't be found."""
    mock_get_config.return_value = [MOCK_USER]
    res = instance.make_string(MOCK_PR)
    expected = (
        f"*This PR is older than 30 days. Consider closing it:*"
        f"\nPull Request: <{MOCK_PR.url}|{MOCK_PR.title}>\nAuthor: mock user"
    )
    assert res == expected


@patch("slack_reminder_api.pr_reminder.PRReminder.make_string")
@patch("slack_reminder_api.pr_reminder.PRReminder.get_reactions")
def test_construct_messages(mock_get_reactions, mock_make_string, instance):
    """Test the correct messages are returned"""
    mock_make_string.return_value = "mock_string"
    mock_get_reactions.return_value = ["mock_reaction"]
    res = instance.construct_messages([MOCK_PR])
    assert res == [Message(text="mock_string", reactions=["mock_reaction"])]


def test_add_reactions(instance):
    """Test reaction add calls are made."""
    instance.client.reactions_add.return_value = {"ok": True}
    instance.add_reactions("mock_timestamp", "mock_channel", ["mock_reaction"])
    instance.client.reactions_add.assert_called_once_with(
        channel="mock_channel", name="mock_reaction", timestamp="mock_timestamp"
    )


def test_add_reactions_fails(instance):
    """Test reaction add calls are made and fail."""
    instance.client.reactions_add.return_value = {"ok": False, "error": "mock_error"}
    with pytest.raises(RuntimeError):
        instance.add_reactions("mock_timestamp", "mock_channel", ["mock_reaction"])


@patch("slack_reminder_api.pr_reminder.PRReminder.add_reactions")
def test_send_message(mock_add_reactions, instance):
    """Test the chat post message is called with the correct parameters"""
    mock_response = MagicMock()
    mock_response.data = {"ts": "mock_timestamp", "channel": "mock_channel"}
    instance.client.chat_postMessage.return_value = mock_response

    res = instance.send_message(
        "mock_text", "mock_channel", ["mock_reaction"], "mock_timestamp"
    )
    instance.client.chat_postMessage.assert_called_once_with(
        text="mock_text",
        channel="mock_channel",
        unfurl_links=False,
        thread_ts="mock_timestamp",
    )
    mock_add_reactions.assert_called_once_with(
        "mock_timestamp", "mock_channel", ["mock_reaction"]
    )
    assert res == mock_response


@patch("slack_reminder_api.pr_reminder.PRReminder.add_reactions")
def test_send_message_fails(_, instance):
    """Test an exception is raised if the message fails to send."""
    mock_response = {"ok": False, "error": "mock_error"}
    instance.client.chat_postMessage.return_value = mock_response
    with pytest.raises(RuntimeError):
        instance.send_message(
            "mock_text", "mock_channel", ["mock_reaction"], "mock_timestamp"
        )


@patch("slack_reminder_api.pr_reminder.PRReminder.construct_messages")
@patch("slack_reminder_api.pr_reminder.PRReminder.send_message")
def test_run(mock_send_message, mock_construct_messages, instance):
    """Test run calls all methods."""
    mock_construct_messages.return_value = [
        Message(text="mock_text", reactions=["mock_reaction"])
    ]
    mock_prs = [MOCK_PR, MOCK_PR_2]
    instance.run(mock_prs, "mock_channel")
    mock_construct_messages.assert_called_once_with([MOCK_PR, MOCK_PR_2])
    mock_send_message.assert_any_call(
        text="Here are the outstanding PRs as of today:", channel="mock_channel"
    )
    mock_send_message.assert_any_call(
        text="mock_text",
        channel="mock_channel",
        reactions=["mock_reaction"],
        timestamp=mock_send_message.call_args_list[1].kwargs["timestamp"],
    )


@patch("slack_reminder_api.pr_reminder.PRReminder.construct_messages")
@patch("slack_reminder_api.pr_reminder.PRReminder.send_message")
def test_run_none_found(mock_send_message, mock_construct_messages, instance):
    """Test run calls send message for no messages"""
    mock_construct_messages.return_value = [
        Message(text="mock_text", reactions=["mock_reaction"])
    ]
    mock_prs = []
    instance.run(mock_prs, "mock_channel")
    mock_send_message.assert_called_once_with(
        text="No Pull Requests were found.", channel="mock_channel"
    )


@patch("slack_reminder_api.pr_reminder.PRReminder.construct_messages")
@patch("slack_reminder_api.pr_reminder.PRReminder.send_message")
def test_run_none_found_no_message(
    mock_send_message, mock_construct_messages, instance
):
    """Test run calls no methods."""
    mock_construct_messages.return_value = [
        Message(text="mock_text", reactions=["mock_reaction"])
    ]
    mock_prs = []
    instance.run(mock_prs, "mock_channel", message_no_prs=False)
    mock_send_message.assert_not_called()
