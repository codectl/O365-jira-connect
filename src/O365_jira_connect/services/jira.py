import base64
import io
import logging
import os
import tempfile
import typing

import jira.resources
import O365
import requests
from jira import JIRA

from O365_jira_connect.models import Issue

__all__ = ("JiraSvc",)

logger = logging.getLogger(__name__)


class ProxyJIRA(JIRA):
    """Proxy class for Jira."""

    def __init__(self, **kwargs):
        super().__init__(
            options={
                "rest_path": "api",
                "rest_api_version": 3,
                "agile_rest_path": jira.resources.AgileResource.AGILE_BASE_REST_PATH,
                "agile_rest_api_version": "latest",
            },
            **kwargs,
        )

    def exists_issue(self, issue_id) -> bool:
        try:
            self.issue(id=issue_id)
        except jira.exceptions.JIRAError as ex:
            if ex.status_code == requests.codes.not_found:
                return False
        else:
            return True

    def has_permissions(self, permissions: list[str], **kwargs) -> bool:
        try:
            data = self.my_permissions(permissions=",".join(permissions), **kwargs)
        except jira.JIRAError:
            return False
        else:
            return all(p in data["permissions"] for p in permissions) and all(
                data["permissions"][p]["havePermission"] for p in permissions
            )

    def board_configuration(self, board_id) -> dict:
        """Get the configuration from a given board

        :param board_id: the Jira id of the board
        :return: the board configuration
        """
        url = self._get_url(f"board/{board_id}/configuration", base=self.AGILE_BASE_URL)
        return self._session.get(url).json()

    @staticmethod
    def create_jql_query(
        assignee: str = None,
        filters: list[str] = None,
        expand: list[str] = None,
        key: typing.Union[str, list[str]] = None,
        labels: list[str] = None,
        status: str = None,
        summary: str = None,
        watcher: str = None,
        sort: str = None,
        **_,
    ):
        """Build jql query based on a provided searching parameters.

        :param assignee: the assignee key (e.g. email)
        :param expand: the expand fields (enum: ['renderedFields'])
        :param filters: the filter ids to apply
        :param key: the Jira ticket key
        :param labels: base labels to search for
        :param status: the status key
        :param summary: the text search
        :param watcher: the watcher key (e.g. email)
        :param sort: sorting criteria (enum: ['created'])
        """
        jql = ""
        if assignee:
            jql = f"{jql}&assignee={assignee}"
        if expand:
            jql = f"{jql}&expand={','.join(expand)}"
        if filters:
            jql = f"{jql}&filter in ({', '.join(filters)})"
        if key:
            joined_keys = ", ".join(key) if isinstance(key, list) else key
            jql = f"{jql}&key in ({joined_keys})"
        if labels:
            joined_labels = ", ".join(labels)
            jql = f"{jql}&labels in ({joined_labels})"
        if status:
            jql = f"{jql}&status='{status}'"
        if summary:
            jql = f"{jql}&summary ~ '{summary}'"
        if watcher:
            jql = f"{jql}&watcher=" + watcher
        if sort:
            jql = f"{jql} ORDER BY {sort}"

        # remove trailing url character
        jql = jql.lstrip("&")

        return jql

    @property
    def markdown(self):
        return JiraMarkdown(parent=self)


class JiraMarkdown(ProxyJIRA):
    def __init__(self, parent=None, **kwargs):
        if parent and isinstance(parent, ProxyJIRA):
            self.__dict__.update(parent.__dict__)
        else:
            super().__init__(**kwargs)

    @staticmethod
    def mention(user):
        """Create Jira markdown mention out of a user.

        If user does not exist, create email markdown.
        """
        if isinstance(user, jira.User):
            return f"[~accountid:{user.accountId}]"
        elif isinstance(user, str):
            return "".join(("[", user, ";|", "mailto:", user, "]"))
        else:
            return None


class JiraSvc(ProxyJIRA):
    """Service to handle Jira operations."""

    def __init__(self, **kwargs):
        super().__init__(
            server=kwargs.pop("server", os.environ["JIRA_PLATFORM_URL"]),
            basic_auth=kwargs.pop(
                "basic_auth",
                (
                    os.environ["JIRA_PLATFORM_USER"],
                    os.environ["JIRA_PLATFORM_TOKEN"],
                ),
            )
            ** kwargs,
        )

    def add_attachment(
        self,
        issue: typing.Union[jira.Issue, str],
        attachment: O365.message.MessageAttachment,
        filename: str = None,
    ) -> typing.Optional[jira.resources.Attachment]:
        """Add attachment considering different types of files."""
        content = None
        if isinstance(attachment, O365.message.MessageAttachment):
            filename = filename or attachment.name
            if not attachment.content:
                logger.warning(f"Attachment '{filename}' is empty")
            else:
                content = base64.b64decode(attachment.content)
        else:
            logger.warning(f"'{type(attachment)}' is not a supported attachment type.")

        # no point on adding empty file
        if content:
            file = tempfile.TemporaryFile()
            file.write(content)
            file.seek(0)
            fi = io.FileIO(file.fileno())
            return super().add_attachment(
                issue=str(issue),
                attachment=io.BufferedReader(fi),
                filename=filename,
            )

    def add_watchers(self, issue: Issue, watchers: list[jira.User] = None):
        """Add a list of watchers to a ticket.

        :param issue: the Jira issue
        :param watchers:
        """
        # add watchers iff has permission
        if self.has_permissions(permissions=["MANAGE_WATCHERS"]):
            for watcher in watchers or []:
                if isinstance(watcher, jira.User):
                    try:
                        self.add_watcher(issue=issue.key, watcher=watcher.accountId)
                    except jira.exceptions.JIRAError as e:
                        if e.status_code not in (
                            requests.codes.unauthorized,
                            requests.codes.forbidden,
                        ):
                            raise e
                        else:
                            name = watcher.displayName
                            logger.warning(
                                f"Watcher '{name}' has no permission to watch issue "
                                f"'{str(issue)}'."
                            )
        else:
            logger.warning("The principal has no permission to manage watchers.")

    def resolve_email(self, email) -> typing.Union[jira.resources.User, str]:
        """Translation given email into Jira user."""
        users = self.search_users(query=email, maxResults=1) if email else []
        return next(iter(users), email)
