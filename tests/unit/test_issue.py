import pytest

from O365_jira_connect.services.issue import IssueSvc


@pytest.fixture
def issue_s():
    return IssueSvc()


class TestIssueSvc:
    def test_create_message_body_with_jira_template(self, issue_s):
        body = issue_s.create_message_body(
            template="jira",
            values={
                "author": "me@example.com",
                "cc": "him@example.com",
                "body": "some short message body",
            },
        )
        assert "From: me@example.com" in body
        assert "Cc: him@example.com" in body
        assert "some short message body" in body

    def test_create_message_body_with_notification_template(self, issue_s):
        url = "issuetracker/issues/UT-123"
        body = issue_s.create_message_body(
            template="notification",
            values={
                "username": "User",
                "summary": "some generic issue summary",
                "key": "UT-123",
                "url": url,
            },
        )
        assert "Dear User" in body
        assert f"the issue [UT-123]({url}) was created." in body
        assert f"track the progress of the issue [here]({url}) was created." in body

    def test_create_message_body_with_reply_template(self, issue_s):
        body = issue_s.create_message_body(
            template="reply",
            values={
                "style": "",
                "body": "some generic body issue",
                "author": "User",
                "reply": "this is a message reply",
            },
        )
        assert "some generic body issue" in body
        assert "this is a message reply" in body
