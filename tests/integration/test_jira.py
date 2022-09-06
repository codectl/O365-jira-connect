import tempfile

import jira
import O365
import pytest

from tests.conftest import JiraTestCase


@pytest.fixture
def issue(jira_s, project, issue_type, request):
    issue = jira_s.create_issue(
        summary="Some dummy issue",
        project=project.id,
        issuetype=issue_type,
    )
    request.cls.issue = issue
    yield issue
    issue.delete()


class TestJiraSvc(JiraTestCase):
    @pytest.mark.usefixtures("issue", "issue_type")
    def test_exists_issue(self):
        issue = self.jira_s.create_issue(
            summary="Yet another dummy issue",
            project=self.project,
            issuetype=self.issue_type,
        )
        assert self.jira_s.exists_issue(issue.id) is True
        issue.delete()
        assert self.jira_s.exists_issue(issue.id) is False
        assert self.jira_s.exists_issue("000") is False

    def test_has_permissions(self):
        assert self.jira_s.has_permissions(["BROWSE_PROJECTS", "CREATE_ISSUES"]) is True
        assert self.jira_s.has_permissions(["INVALID_PERMISSION"]) is False

    @pytest.mark.usefixtures("issue")
    def test_add_attachment(self):
        protocol = O365.MSGraphProtocol()  # dummy protocol
        file = tempfile.NamedTemporaryFile()
        file.write(b"some dummy data")
        file.seek(0)
        file = O365.message.MessageAttachment(protocol=protocol, attachment=file.name)
        attachment = self.jira_s.add_attachment(issue=self.issue, attachment=file)
        issue = self.jira_s.issue(id=self.issue.id)
        assert len(issue.fields.attachment) == 1
        assert issue.fields.attachment[0].id == attachment.id
        assert self.jira_s.attachment(id=attachment.id).get() == b"some dummy data"

    @pytest.mark.usefixtures("issue")
    def test_add_watchers(self):
        self.jira_s.add_watchers(issue=self.issue, watchers=[self.guest_user])
        watchers = self.jira_s.watchers(issue=self.issue)
        assert watchers.watchCount == 2
        assert watchers.watchers[0].accountId == self.guest_user.accountId
