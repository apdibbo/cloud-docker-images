"""
This module uses Socket Mode to enable the code to run locally and not need to be open to the internet.
"""

import logging
import argparse
from argparse import Namespace

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from helper.errors import NoTestCase
from helper.read_config import validate_required_files, get_config, get_token
from events import run_global_reminder, run_personal_reminder

logging.basicConfig(level=logging.DEBUG)


def run_methods(args) -> None:
    """
    Test each event given in args.
    :param args: CLI Arguments
    """
    if getattr(args, "global") and not args.channel:
        raise ValueError("If using --global then --channel is required")

    for arg, value in vars(args).items():
        if value:
            call_method(arg, args)


def call_method(event: str, args: Namespace) -> None:
    """
    Run the test logic for each event.
    :param event: The event to test
    :param args: CLI Arguments
    """
    match event:
        case "channel":
            # Catch case for the required parameter "channel".
            # Nothing should run here as channel is an arg of other tests
            pass
        case "global":
            run_global_reminder(args.channel)
        case "personal":
            users = get_config("users")
            run_personal_reminder(users)
        case _:
            raise NoTestCase(f"There is not test case for {event}")


def main(args: Namespace) -> None:
    """
    This function checks the config files, runs the tests, then starts the app.
    :param args: Command line interface arguments
    """
    logging.info("Running tests")
    run_methods(args)
    logging.info("Completed tests.")
    logging.info("Running Slack App")

    app = App(token=get_token("SLACK_BOT_TOKEN"))
    handler = SocketModeHandler(app, get_token("SLACK_APP_TOKEN"))
    handler.start()


def parse_args() -> Namespace:
    """Create and collect arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", help="Channel to send messages to.")
    parser.add_argument(
        "--global", help="Test the global reminder", action="store_true"
    )
    parser.add_argument(
        "--personal", help="Test the personal reminder", action="store_true"
    )
    return parser.parse_args()


if __name__ == "__main__": # pragma: no cover
    arguments = parse_args()
    validate_required_files()
    main(arguments)
