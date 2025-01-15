"""
This module declares the dataclass used to store PR information.
This is preferred over dictionaries as dataclasses make code more readable.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class PR:
    """Class holding information about a single pull request."""

    # Disabling as we need more than 8 attributes
    # pylint: disable = R0902
    title: str
    author: str
    url: str
    created_at: datetime
    draft: bool
    stale: bool
    repository: str
    labels: List[str]

    @classmethod
    def from_json(cls, data: Dict):
        """
        Serialise the JSON data into this dataclass structure.
        :param data: JSON | Dict HTTP response data
        :return:
        """
        created_at = datetime.strptime(data["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        return cls(
            title=f"{data['title']} #{data['number']}",
            author=data["user"]["login"],
            url=data["html_url"],
            stale=cls.is_stale(created_at),
            created_at=created_at,
            draft=data["draft"],
            labels=[label["name"] for label in data["labels"]],
            repository=data["html_url"].split(sep="/")[5],
        )

    @staticmethod
    def is_stale(created_at: datetime) -> bool:
        """
        Returns if a PR is stale or not.
        :param created_at: When the PR was created
        """
        opened_date = created_at.replace(tzinfo=None)
        datetime_now = datetime.now().replace(tzinfo=None)
        time_cutoff = datetime_now - timedelta(days=30)
        return opened_date <= time_cutoff


@dataclass
class Message:
    """Ready to send message data"""

    text: str
    reactions: List[str]


@dataclass
class User:
    """Class to store user information"""

    real_name: str
    github_name: str
    slack_id: str

    @classmethod
    def from_config(cls, info: Dict):
        """Create a user class from the app config."""
        return cls(
            real_name=info["real_name"],
            github_name=info["github_name"],
            slack_id=info["slack_id"],
        )


def sort_by(
    obj_list: List[PR | User], prop: str, reverse: bool = False
) -> List[PR | User]:
    """
    Sort the list of Dataclasses by property.
    :param obj_list: List of Dataclasses
    :param prop: Property to sort by
    :param reverse: To sort in reverse
    :return: List of Dataclasses
    """
    try:
        return sorted(obj_list, key=lambda obj: getattr(obj, prop), reverse=reverse)
    except AttributeError as exc:
        raise ValueError(f"Unable to sort list by {prop}") from exc


def filter_by(obj_list: List[PR | User], prop: str, value: str) -> List[PR | User]:
    """
    Filter the list of Dataclass objects by property.
    :param obj_list: List of Dataclass objects
    :param prop: Property to filter by
    :param value: Value to evaluate filter.
    :return: Filtered list of Dataclasses.
    """
    try:
        return list(filter(lambda obj: getattr(obj, prop) == value, obj_list))
    except AttributeError as exc:
        raise ValueError(f"Unable to filter list by {prop}") from exc
