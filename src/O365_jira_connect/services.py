import base64
import datetime
import io
import logging
import os
import tempfile
import typing

import jira.resources
import O365
import requests
from jira import JIRA

from O365_jira_connect.components import with_session
from O365_jira_connect.models import Issue

__all__ = ("IssueSvc", "JiraSvc")

logger = logging.getLogger(__name__)


class IssueSvc:
    @classmethod
    @with_session
    def create(
        cls, session=None, configs=None, attachments: list = None, **kwargs
    ) -> Issue:
        """Create a new issue by calling Jira API to create a new
        issue. A new local reference to the issue is also created.

        :param session: injected ORM session
        :param configs: config settings
        :param attachments: the files to attach to the issue which
                            are stored in Jira
        :param kwargs: properties of the issue
            title: title of the issue
            description: body of the issue
            reporter: email of the author's issue
            board: board key which the issue belongs to
            labels: which labels assign to issue
            priority: severity of the issue
            watchers: user emails to watch for issue changes
        """
        svc = JiraSvc()

        # translate emails into jira.User objects
        reporter = cls.resolve_email(email=kwargs.get("reporter"))
        watchers = [
            cls.resolve_email(email, default=email)
            for email in kwargs.get("watchers") or []
        ]

        # create issue body with Jira markdown format
        body = cls.create_message_body(
            template="jira.j2",
            values={
                "author": svc.markdown.mention(user=reporter or kwargs.get("reporter")),
                "cc": " ".join(svc.markdown.mention(user=w) for w in watchers),
                "body": kwargs.get("body"),
            },
        )

        # if reporter is not a Jira account, reporter is set to 'Anonymous'
        reporter_id = getattr(reporter, "accountId", None)

        # set defaults
        board = next(b for b in svc.boards() if b.key == kwargs.get("board"))
        priority_opt = ["high", "low"]
        priority = (kwargs.get("priority") or "").lower()
        priority = {"name": priority.capitalize()} if priority in priority_opt else None
        labels = kwargs.get("labels", []) + configs["JIRA_DEFAULT_LABELS"]

        # create ticket in Jira
        issue = svc.create_issue(
            summary=kwargs.get("title"),
            description=body,
            reporter={"id": reporter_id},
            project={"key": board.project},
            issuetype={"name": configs["JIRA_ISSUE_TYPE"]},
            labels=labels,
            **{"priority": priority} if priority else {},
        )

        # add watchers
        svc.add_watchers(issue=issue, watchers=watchers)

        # adding attachments
        for attachment in attachments or []:
            svc.add_attachment(issue=issue, attachment=attachment)

        # add new entry to the db
        local_fields = {k: v for k, v in kwargs.items() if k in Issue.__dict__}
        issue = Issue(key=issue.key, **local_fields)

        session.add(issue)
        session.commit()

        logger.info(f"Created issue '{issue.key}'.")

        return cls.find_one(key=issue.key)

    @staticmethod
    @with_session
    def get(ticket_id, session=None) -> typing.Optional[Issue]:
        return session.query(Issue).get(ticket_id)

    @classmethod
    def find_one(cls, **filters) -> typing.Optional[Issue]:
        """Search for a single ticket based on several criteria."""
        return next(iter(cls.find_by(limit=1, **filters)), None)

    @classmethod
    @with_session
    def find_by(
        cls,
        session=None,
        limit: int = 20,
        fields: list = None,
        _model: bool = False,
        **filters,
    ) -> list[Issue]:
        """Search for tickets based on several criteria.

        Jira's filters are also supported.

        :param session: injected ORM session
        :param limit: the max number of results retrieved
        :param fields: additional fields to include in results schema
        :param _model: whether to return a ticket model or cross results Jira data
        :param filters: the query filters
        """
        svc = JiraSvc()

        # split filters
        native_filters = (
            "assignee",
            "filters",
            "labels",
            "key",
            "q",
            "sort",
            "status",
            "watcher",
        )
        local_filters = {k: v for k, v in filters.items() if k in Issue.__dict__}
        jira_filters = {k: v for k, v in filters.items() if k in native_filters}

        if _model:
            return session.query(Issue).filter_by(**local_filters).all()
        else:
            # if any of the filter is not a Jira filter, then
            # apply local filter and pass on results to jql
            if local_filters:
                issues = session.query(Issue).filter_by(**local_filters).all()

                # skip routine if no local entries are found
                if not issues:
                    return []
                jira_filters["key"] = [issue.key for issue in issues]

            # fetch tickets from Jira using jql while skipping jql
            # validation since local db might not be synched with Jira
            query = svc.create_jql_query(
                summary=filters.pop("q", None),
                **jira_filters,
            )

            # include additional fields
            fields = fields or []
            if "*navigable" not in fields:
                fields.append("*navigable")
            rendered = "renderedFields" if "rendered" in fields else "fields"

            issues = []  # container for issues result

            jira_issues = svc.search_issues(
                jql_str=query,
                maxResults=limit,
                validate_query=False,
                fields=fields,
                expand=rendered,
            )

            for jira_issue in jira_issues:
                issue = cls.find_one(key=jira_issue.key, _model=True)

                # prevent cases where local db is not synched with Jira
                # for cases where Jira tickets are not yet locally present
                if issue:
                    issue.jira_issue = jira_issue

                    # add watchers if requested
                    if "watchers" in fields:
                        watchers = svc.watchers(jira_issue.key)
                        issue.jira_issue.raw["watchers"] = watchers.raw["watchers"]

                    issues.append(issue)
            return issues

    @classmethod
    @with_session
    def update(cls, issue_id, session=None, **kwargs):
        issue = cls.get(issue_id=issue_id)
        for key, value in kwargs.items():
            if hasattr(issue, key):
                setattr(issue, key, value)
        session.commit()

        msg = f"Updated issue '{issue.key}' with the attributes: '{kwargs}'."
        logger.info(msg)

    @classmethod
    @with_session
    def delete(cls, issue_id, session=None):
        issue = cls.get(issue_id=issue_id)
        if issue:
            session.delete(issue)
            session.commit()

            logger.info(f"Deleted issue '{issue.key}'.")

    @staticmethod
    def add_message_to_history(message: O365.Message, model: Issue):
        """Add a message to the issue history."""
        messages_id = model.outlook_messages_id.split(",")
        if message.object_id not in messages_id:
            IssueSvc.update(
                issue_id=model.id,
                outlook_messages_id=",".join(messages_id + [message.object_id]),
                updated_at=datetime.datetime.utcnow(),
            )

    @classmethod
    def create_comment(
        cls,
        issue: typing.Union[Issue, str],
        author: str,
        body: str,
        watchers: list = None,
        attachments: list = None,
    ):
        """Create the body of the ticket.

        :param issue: the issue to comment on
        :param author: the author of the comment
        :param body: the body of the comment
        :param watchers: user emails to watch for issue changes
        :param attachments: the files to attach to the comment which
                            are stored in Jira
        """
        svc = JiraSvc()

        # translate watchers into jira.User objects iff exists
        watchers = [cls.resolve_email(email, default=email) for email in watchers or []]

        body = cls.create_message_body(
            template="jira.j2",
            values={
                "author": svc.markdown.mention(user=author),
                "cc": " ".join(
                    svc.markdown.mention(user=watcher) for watcher in watchers
                ),
                "body": body,
            },
        )
        svc.add_comment(issue=issue, body=body, is_internal=True)

        # add watchers
        svc.add_watchers(issue=issue, watchers=watchers)

        # adding attachments
        for attachment in attachments or []:
            svc.add_attachment(issue=issue, attachment=attachment)

    @staticmethod
    def create_message_body(template=None, values=None) -> typing.Optional[str]:
        """Create the body of the ticket.

        :param template: the template to build ticket body from
        :param values: values for template interpolation
        """
        if not template:
            return None

        template_path = os.path.join(
            current_app.root_path, "templates", "ticket", "format"
        )
        template_filepath = os.path.join(template_path, template)
        if not os.path.exists(template_filepath):
            raise ValueError("Invalid template provided")

        with open(template_filepath) as file:
            content = file.read()

        return jinja2.Template(content).render(**values)

    @staticmethod
    def resolve_email(email, default=None) -> jira.resources.User:
        """Email translation to Jira user."""
        return next(iter(JiraSvc().search_users(query=email, maxResults=1)), default)


class ProxyJIRA(JIRA):
    """Proxy class for Jira."""

    def __init__(self, **kwargs):
        url = kwargs.pop("url")
        user = kwargs.pop("user")
        token = kwargs.pop("token")
        super().__init__(
            server=url,
            basic_auth=(user, token),
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

    def my_permissions(
        self,
        project_key=None,
        project_id=None,
        issue_key=None,
        issue_id=None,
        permissions=None,
    ):
        """Override.

        :param project_key: see overridden method
        :param project_id: see overridden method
        :param issue_key: see overridden method
        :param issue_id: see overridden method
        :param permissions: limit returned permissions to the specified permissions.
                            Change introduce by Jira as per early 2020.
        """
        params = {}
        if project_key is not None:
            params["projectKey"] = project_key
        if project_id is not None:
            params["projectId"] = project_id
        if issue_key is not None:
            params["issueKey"] = issue_key
        if issue_id is not None:
            params["issueId"] = issue_id
        if permissions is not None:
            params["permissions"] = permissions
        return self._get_json("mypermissions", params=params)

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

    def __init__(
        self,
        url=None,
        user=None,
        token=None,
        **kwargs,
    ):
        url = url or os.environ["JIRA_PLATFORM_URL"]
        user = user or os.environ["JIRA_PLATFORM_USER"]
        token = token or os.environ["JIRA_PLATFORM_TOKEN"]
        super().__init__(
            url=url,
            user=user,
            token=token,
            **kwargs,
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
        if self.has_permissions(permissions=["MANAGE_WATCHERS"], issue_key=str(issue)):
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
