"""This module contains custom exceptions to handle errors for the Application."""


class RepoNotFound(LookupError):
    """Error: The requested repository does not exist on GitHub."""


class UnknownHTTPError(RuntimeError):
    """Error: The received HTTP response is unexpected."""


class RepositoriesNotGiven(RuntimeError):
    """Error: repos supplied is empty does not contain any repositories."""


class TokensNotGiven(RuntimeError):
    """Error: Token values are either empty or not given."""


class UserMapNotGiven(RuntimeError):
    """Error: User map is empty."""


class BadGitHubToken(RuntimeError):
    """Error: GitHub REST Api token is invalid."""


class ChannelNotFound(LookupError):
    """Error: The channel was not found."""


class UserNotFound(LookupError):
    """Error: The Slack member was not found."""


class FailedToPostMessage(RuntimeError):
    """Error: Failed to post message to Slack."""


class NoUsersGiven(RuntimeError):
    """Error: No users to post to."""
