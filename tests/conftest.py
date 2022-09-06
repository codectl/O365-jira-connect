import os

import jira
import pytest
import unittest

from O365_jira_connect.services.jira import JiraSvc


@pytest.fixture(scope="class")
def jira_s(request):
    jira_s = JiraSvc(
        server=os.environ["JIRA_PLATFORM_URL"],
        basic_auth=(
            os.environ["JIRA_PLATFORM_USER"],
            os.environ["JIRA_PLATFORM_TOKEN"],
        ),
    )
    request.cls.jira_s = jira_s
    return jira_s


@pytest.fixture(scope="class")
def project(jira_s, request):
    try:
        project = jira_s.create_project(key="UT", name="UNITTESTS")
    except jira.JIRAError as ex:
        if ex.status_code not in (400, 500):
            raise ex
        else:
            # suppress 400: project exists error
            # suppress 500: issue #1480 (pycontribs/jira)
            pass
        project = jira_s.project(id="UT")
    request.cls.project = project
    return project


@pytest.fixture(scope="class")
def issue_type(jira_s, request):
    issue_type = os.environ.get("JIRA_ISSUE_TYPE", "Task")
    request.cls.issue_type = issue_type
    return issue_type


@pytest.mark.usefixtures("jira_s", "project", "issue_type")
class JiraTestCase(unittest.TestCase):
    def setUp(self):
        # add a guest user
        self.jira_s.add_user(username="guest", email="guest@example.com")
        self.guest_user = next(self.jira_s.search_users(query="guest"))

    def tearDown(self):
        self.jira_s.delete_project(self.project)
