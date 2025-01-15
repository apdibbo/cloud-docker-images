"""Tests for find_prs.py"""

from unittest.mock import patch, NonCallableMock
from datetime import datetime
import pytest
from requests.exceptions import HTTPError
from helper.data import PR, sort_by, filter_by
from find_pr_api.github import FindPRs


# pylint: disable=R0801
@pytest.fixture(name="instance", scope="function")
def instance_fixture():
    """Creates a class fixture to use in the tests"""
    return FindPRs()


@patch("find_pr_api.github.PR")
@patch("find_pr_api.github.FindPRs.make_request")
def test_run(mock_make_request, mock_data, instance):
    """Tests the run method returns the correct object"""
    mock_repo_1 = NonCallableMock()
    mock_repo_2 = NonCallableMock()
    mock_repo_1.created_at = 1
    mock_repo_2.created_at = 2
    mock_repos = [mock_repo_2, mock_repo_1]
    res = instance.run(mock_repos, "mock_token")
    res = sort_by(res, "created_at", True)

    for repo in mock_repos:
        mock_make_request.assert_any_call(repo, "mock_token")

    mock_res = list(reversed([call.return_value for call in mock_data.call_arg_list]))
    assert res == mock_res


@patch("find_pr_api.github.requests")
def test_make_request(mock_requests, instance):
    """Test that requests are made and errors are raised."""
    mock_ok_request = NonCallableMock()
    mock_error_request = NonCallableMock()
    mock_error_request.raise_for_status.side_effect = HTTPError
    mock_requests.get.side_effect = [mock_ok_request, mock_error_request]
    res = instance.make_request(
        "https://api.github.com/repos/mock_owner/mock_repo/pulls", "mock_token"
    )
    assert res == mock_ok_request.json.return_value
    with pytest.raises(HTTPError):
        instance.make_request(
            "https://api.github_wrong.com/repos/mock_owner/mock_repo/pulls",
            "mock_token",
        )


MOCK_PR_1 = PR(
    title="mock_title #1",
    author="mock_author",
    url="https://api.github.com/repos/mock_owner/mock_repo/pulls",
    stale=False,
    draft=False,
    labels=["mock_label"],
    repository="mock_repo",
    created_at=datetime.strptime("2024-11-15T07:33:56Z", "%Y-%m-%dT%H:%M:%SZ"),
)
MOCK_PR_2 = PR(
    title="mock_title #2",
    author="mock_author_2",
    url="https://api.github.com/repos/mock_owner/mock_repo/pulls",
    stale=True,
    draft=True,
    labels=["mock_label"],
    repository="mock_repo_2",
    created_at=datetime.strptime("2024-10-15T07:33:56Z", "%Y-%m-%dT%H:%M:%SZ"),
)


def test_sort_by():
    """Test the list is sorted correctly."""
    mock_pr_list = [MOCK_PR_1, MOCK_PR_2]
    res = sort_by(mock_pr_list, "created_at")
    assert res == list(reversed(mock_pr_list))

    res_reversed = sort_by(mock_pr_list, "created_at", True)
    assert res_reversed == mock_pr_list


def test_sort_by_fails():
    """Test sort raises an error when sorting by unknown attribute"""
    mock_pr_list = [MOCK_PR_1, MOCK_PR_2]
    with pytest.raises(ValueError):
        sort_by(mock_pr_list, "unknown")


def test_filter_by():
    """Test the list is filtered correctly."""
    mock_pr_list = [MOCK_PR_1, MOCK_PR_2]
    res = filter_by(mock_pr_list, "repository", "mock_repo")
    assert res == [MOCK_PR_1]


def test_filter_by_fails():
    """Test filter raises an error when filtering by unknown attribute"""
    mock_pr_list = [MOCK_PR_1, MOCK_PR_2]
    with pytest.raises(ValueError):
        filter_by(mock_pr_list, "unknown", "some_value")
