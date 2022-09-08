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
    pass
