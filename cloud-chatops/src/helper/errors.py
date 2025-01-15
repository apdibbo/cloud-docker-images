"""This module contains custom exceptions to handle errors for the app."""


class ErrorInConfig(RuntimeError):
    """An error in the config set up."""


class NoTestCase(LookupError):
    """Error: There is no method to test this event."""
