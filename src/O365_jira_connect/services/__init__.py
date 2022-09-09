from O365_jira_connect.services.issue import IssueSvc
from O365_jira_connect.services.jira import JiraSvc

__all__ = ("issue_s", "jira_s")

# initialize internal service components
jira_s = JiraSvc()
issue_s = IssueSvc(jira=jira_s)
