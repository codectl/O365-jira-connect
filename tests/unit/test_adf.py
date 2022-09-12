import jinja2
import pytest

from O365_jira_connect.templates.adf import TemplateBuilder


@pytest.fixture
def builder():
    return TemplateBuilder()


class TestTemplateBuilder:
    def test_issue_body_template(self, builder):

        doc = builder.jira_issue_body_template(
            author="me@example.com",
            cc=["him@example.com", "her@example.com"],
            body="some short message body"
        )
        paragraph1 = doc["content"][0]["content"]
        paragraph2 = doc["content"][1]["content"]
        assert any(c.get("text") == "me@example.com" for c in paragraph1)
        assert any(c.get("text") == "him@example.com" for c in paragraph1)
        assert any(c.get("text") == "her@example.com" for c in paragraph1)
        assert paragraph2[0]["text"] == "some short message body"

    def test_message_notification_template(self, builder):

        url = "https://issuetracker.com"
        doc = builder.outlook_message_notification_template(
            username="unittests",
            issue_key="UT-123",
            summary="the issue summary",
            url=url,
        )
        text = doc["content"][0]["content"][0]["text"]
        assert "Dear unittests" in text
        assert f"the issue [UT-123]({url}) was created." in text
        assert f"track the progress of the issue [here]({url})" in text

    def test_message_reply_template(self, builder):
        doc = builder.outlook_message_reply_template(
            style="",
            body="some generic body issue",
            author="User",
            reply="this is a message reply",
        )
        text = doc["content"][0]["content"][0]["text"]
        assert "some generic body issue" in text
        assert "this is a message reply" in text

    def test_missing_template_raises_exception(self, builder):
        with pytest.raises(jinja2.exceptions.TemplateNotFound):
            builder.render(template="missing", values={})
