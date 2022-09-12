import pytest

from O365_jira_connect.services.issue import IssueSvc


@pytest.fixture
def issue_s():
    return IssueSvc()


class TestIssueSvc:
    pass
