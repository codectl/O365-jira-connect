import pytest

from O365_jira_connect.services.issue import IssueSvc


@pytest.fixture
def issue_s():
    return IssueSvc()


class TestIssueSvc:
    def test_create_message_body(self, issue_s):
        body = issue_s.create_message_body(template="jira", values={
            "author": "me@example.com",
            "cc": "him@example.com",
            "body": "some short body"}
                                           )
        print(body)
