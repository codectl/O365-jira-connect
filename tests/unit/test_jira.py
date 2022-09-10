import jira
import pytest
import requests
import requests_mock

from O365_jira_connect.services.jira import AtlassianDF, JiraSvc


@pytest.fixture
def adapter():
    return requests_mock.Adapter()


@pytest.fixture
def jira_s(adapter):
    jira_s = JiraSvc(
        server="https://jira.atlassian.com",
        basic_auth=("test", "xxx"),
        get_server_info=False,
    )
    session = requests.Session()
    session.mount("https://", adapter)
    jira_s._session = session
    return jira_s


class TestJiraSvc:
    def test_exists_issue(self, jira_s, mocker):
        mocker.patch.object(jira_s, "issue", return_value="")
        assert jira_s.exists_issue("Jira-123") is True

        mocker.patch.object(
            jira_s, "issue", side_effect=jira.JIRAError(status_code=404)
        )
        assert jira_s.exists_issue("Jira-123") is False

    def test_has_permissions(self, jira_s, adapter):
        path = jira_s._get_url("mypermissions")
        data = {"permissions": {}}
        adapter.register_uri("GET", path, json=data)
        assert jira_s.has_permissions(permissions=[]) is True
        assert jira_s.has_permissions(permissions=["perm"]) is False
        data["permissions"]["perm1"] = {"havePermission": True}
        adapter.register_uri("GET", path, json=data)
        assert jira_s.has_permissions(permissions=["perm1"]) is True
        assert jira_s.has_permissions(permissions=["perm1", "perm2"]) is False
        data["permissions"]["perm2"] = {"havePermission": False}
        adapter.register_uri("GET", path, json=data)
        assert jira_s.has_permissions(permissions=["perm1"]) is True
        assert jira_s.has_permissions(permissions=["perm2"]) is False
        assert jira_s.has_permissions(permissions=["perm1", "perm2"]) is False

    def test_jql_builder(self, jira_s):
        query = jira_s.create_jql_query(
            assignee="user",
            expand=["renderedFields"],
            filters=["filter1", "filter2"],
            key="JIRA-123",
            labels=["test", "label"],
            sort="created",
            status="open",
            summary="test summary",
            watcher="test",
        )
        assert "assignee=user" in query
        assert "expand=renderedFields" in query
        assert "filter in (filter1, filter2)" in query
        assert "key in (JIRA-123)" in query
        assert "labels in (test, label)" in query
        assert "status='open'" in query
        assert "summary ~ 'test summary'" in query
        assert "watcher=test" in query
        assert "ORDER BY created" in query

    def test_mention(self, jira_s):
        email = "user@xyz.com"
        user = jira.User({}, jira_s._session, raw={"self": {}, "accountId": "123"})
        assert jira_s.markdown.mention(email) == f"[{email};|mailto:{email}]"
        assert jira_s.markdown.mention(user) == "[~accountid:123]"

    def test_document_format(self):
        doc = AtlassianDF()
        doc.node(t="paragraph").node(t="text", text="dummy text")
        norm = doc.normalize()
        assert norm == {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "dummy text"}],
                }
            ],
        }
