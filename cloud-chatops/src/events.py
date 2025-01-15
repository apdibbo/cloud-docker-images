"""
This module contains events to run in main.py.
"""

import os
from typing import List
from slack_sdk import WebClient
from helper.data import User, sort_by, filter_by
from helper.read_config import get_config, get_token
from slack_reminder_api.pr_reminder import PRReminder
from find_pr_api.github import FindPRs


def run_global_reminder(channel: str) -> None:
    """This event sends a message to the specified channel with all open PRs."""
    unsorted_prs = FindPRs().run(
        repos=get_config("repos"), token=get_token("GITHUB_TOKEN")
    )
    prs = sort_by(unsorted_prs, "created_at", False)
    PRReminder(WebClient(token=get_token("SLACK_BOT_TOKEN"))).run(
        prs=prs,
        channel=channel,
    )


def run_personal_reminder(users: List[User], message_no_prs: bool = False) -> None:
    """
    This event sends a message to each user in the user map with their open PRs.
    :param message_no_prs: Send a message saying there are no PRs open.
    :param users: Users to send reminders to.
    """
    unsorted_prs = FindPRs().run(
        repos=get_config("repos"), token=get_token("GITHUB_TOKEN")
    )
    prs = sort_by(unsorted_prs, "created_at", False)
    client = WebClient(token=get_token("SLACK_BOT_TOKEN"))
    for user in users:
        filtered_prs = filter_by(prs, "author", user.github_name)
        PRReminder(client).run(
            prs=filtered_prs,
            channel=user.slack_id,
            message_no_prs=message_no_prs,
        )


def weekly_reminder(reminder_type: str) -> None:
    """
    This function chooses which type of reminder to call based on its arguments.
    :param reminder_type: Type of reminder to send, global or personal.
    """
    if reminder_type == "global":
        channel = get_config("channel")
        run_global_reminder(channel)
    elif reminder_type == "personal":
        run_personal_reminder(users=get_config("users"), message_no_prs=False)
    else:
        raise ValueError(
            f'Reminder type {reminder_type} is not supported. Use either "global" or "personal".'
        )


def slash_prs(ack, respond, command):
    """
    This event sends a message to the user containing open PRs.
    :param command: The return object from Slack API.
    :param ack: Slacks acknowledgement command.
    :param respond: Slacks respond command to respond to the command in chat.
    """
    ack()
    user_id = command["user_id"]
    users = get_config("users")
    if user_id not in [user.slack_id for user in users]:
        respond(
            f"Could not find your Slack ID {user_id} in the user map. "
            f"Please contact the service maintainer to fix this."
        )
        return

    if command["text"] == "mine":
        respond("Gathering the PRs...")
        run_personal_reminder(
            [user for user in users if user.slack_id == user_id], message_no_prs=True
        )
    elif command["text"] == "all":
        respond("Gathering the PRs...")
        run_global_reminder(user_id)
    else:
        respond("Please provide the correct argument: 'mine' or 'all'.")
        return

    respond("Check out your DMs.")


def slash_find_host(ack, respond):
    """
    Responds to the user with the host IP of the machine that received the command.
    :param ack: Slacks acknowledgement command.
    :param respond: Slacks respond command to respond to the command in chat.
    """
    ack()
    host_ip = os.environ.get("HOST_IP")
    respond(f"The host IP of this node is: {host_ip}")
