import tempfile

import O365
import pytest


@pytest.fixture(scope="function")
def issue(jira_s, project, issue_type):
    issue = jira_s.create_issue(
        summary="Some dummy issue",
        project=project.id,
        issuetype=issue_type,
    )
    yield issue
    issue.delete()


class TestJiraSvc:

    @pytest.fixture(scope="class")
    def guest_user(self, jira_s):
        jira_s.add_user(username="guest", email="guest@example.com")
        return next(jira_s.search_users(query="guest"))

    def test_exists_issue(self, jira_s, project, issue_type):
        issue = jira_s.create_issue(
            summary="Yet another dummy issue",
            project=project,
            issuetype=issue_type,
        )
        assert jira_s.exists_issue(issue.id) is True
        issue.delete()
        assert jira_s.exists_issue(issue.id) is False
        assert jira_s.exists_issue("000") is False

    def test_has_permissions(self, jira_s):
        assert jira_s.has_permissions(["BROWSE_PROJECTS", "CREATE_ISSUES"]) is True
        assert jira_s.has_permissions(["INVALID_PERMISSION"]) is False

    def test_add_attachment(self, jira_s, issue):
        protocol = O365.MSGraphProtocol()  # dummy protocol
        file = tempfile.NamedTemporaryFile()
        file.write(b"some dummy data")
        file.seek(0)
        file = O365.message.MessageAttachment(protocol=protocol, attachment=file.name)
        attachment = jira_s.add_attachment(issue=issue, attachment=file)
        assert len(issue.fields.attachment) == 1
        assert issue.fields.attachment[0].id == attachment.id
        assert jira_s.attachment(id=attachment.id).get() == b"some dummy data"

    def test_add_watchers(self, jira_s, issue, guest_user):
        jira_s.add_watchers(issue=issue, watchers=[guest_user])
        watchers = jira_s.watchers(issue=issue)
        assert watchers.watchCount == 2
        assert watchers.watchers[0].accountId == guest_user.accountId
