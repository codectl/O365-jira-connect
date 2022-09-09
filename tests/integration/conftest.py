import os

import jira
import pytest

from O365_jira_connect.services.issue import IssueSvc
from O365_jira_connect.services.jira import JiraSvc


@pytest.fixture(scope="session")
def jira_s():
    return JiraSvc(
        server=os.environ["JIRA_PLATFORM_URL"],
        basic_auth=(
            os.environ["JIRA_PLATFORM_USER"],
            os.environ["JIRA_PLATFORM_TOKEN"],
        ),
    )


@pytest.fixture(scope="session")
def issue_s(jira_s):
    return IssueSvc(jira=jira_s)


@pytest.fixture(scope="session")
def project(jira_s):
    try:
        jira_s.create_project(key="UT", name="UNITTESTS")
    except jira.JIRAError as ex:
        if ex.status_code not in (400, 500):
            raise ex
        else:
            # suppress 400: project exists error
            # suppress 500: issue #1480 (pycontribs/jira)
            pass
    project = jira_s.project(id="UT")
    yield project
    jira_s.delete_project(project)


@pytest.fixture(scope="session")
def issue_type(jira_s):
    return os.environ.get("JIRA_ISSUE_TYPE", "Task")
