"""This module handles reading data from files such as secrets and user maps."""

from typing import Dict, Union, List
import sys
import os
import yaml
from helper.errors import ErrorInConfig
from helper.data import User


def get_path() -> str:
    """
    Determine which path to use for reading secrets.
    This differs between development and production environments.
    :return: The path as a string
    """
    if sys.argv[0].endswith("dev.py"):
        # Using dev secrets here for local testing as it runs the app.
        # in a separate Slack Workspace than the production app.
        # This means the slash commands won't be picked up by the production app.
        try:
            # Try multiple paths for Linux / Windows differences
            return f"{os.environ['HOME']}/dev_cloud_chatops/"
        except KeyError:
            try:
                return f"{os.environ['HOMEPATH']}\\dev_cloud_chatops\\"
            except KeyError as exc:
                raise ErrorInConfig(
                    "Are you trying to run locally? Couldn't find HOME or HOMEPATH in your environment variables."
                ) from exc

    # Production path
    return "/usr/src/app/cloud_chatops/"


def get_token(secret: str) -> str:
    """
    This function reads from the secret's file and returns a specified secret.
    :param secret: The secret to find
    :return: A secret as string
    """
    path = get_path()
    with open(path + "secrets/secrets.yml", "r", encoding="utf-8") as secrets:
        secrets_data = yaml.safe_load(secrets)
        return secrets_data[secret]


def get_config(section: str) -> Union[List, Dict, str]:
    """
    This function returns the specified section from the config file.
    :param section: The section of the config to retrieve.
    :return: The data retrieved from the config file.
    """
    path = get_path()
    with open(path + "config/config.yml", "r", encoding="utf-8") as config:
        config_data = yaml.safe_load(config)
        match section:
            case "users":
                return [User.from_config(user) for user in config_data[section]]
            case "repos":
                data = config_data[section]
                repos = []
                for owner in data:
                    repos += [f"{owner}/{repo}" for repo in data[owner]]
                return repos
            case "channel":
                return config_data[section]
            case _:
                raise KeyError(f"No section in config named {section}.")


def validate_required_files() -> None:
    """
    This function checks that all required files have data in them before the app runs.
    """
    for token in ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "GITHUB_TOKEN"]:
        if not get_token(token):
            raise ErrorInConfig(f"Token {token} does not have a value in secrets.yml.")

    if not get_config("repos"):
        raise ErrorInConfig("config.yml does not contain any repositories.")

    if not get_config("users"):
        raise ErrorInConfig("Users parameter in config.yml is not set.")

    if not get_config("channel"):
        raise ErrorInConfig("Channel parameter in config.yml is not set.")
