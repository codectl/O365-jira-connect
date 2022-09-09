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


class TestIssueSvc:
    @pytest.fixture(scope="class")
    def guest_user(self, jira_s):
        jira_s.add_user(username="guest", email="guest@example.com")
        return next(jira_s.search_users(query="guest"))

    def test_crud(self, issue_s, guest_user):
        issue = issue_s.create(reporter=guest_user)
