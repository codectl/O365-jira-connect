import datetime
import logging
import os
import typing

import jinja2
import O365

from O365_jira_connect import __file__ as pkg
from O365_jira_connect.env import env
from O365_jira_connect.models import Issue
from O365_jira_connect.session import with_session

__all__ = ("IssueSvc",)

logger = logging.getLogger(__name__)


class IssueSvc:
    def __init__(self, jira=None, configs=None):
        self.jira = jira
        self.configs = configs or {
            "project_key": env.str("JIRA_PROJECT_KEY", None),
            "issue_type": env.str("JIRA_ISSUE_TYPE", None),
            "default_labels": env.list("JIRA_DEFAULT_LABELS", [], delimiter=" "),
        }

    @with_session
    def create(self, session=None, attachments: list = None, **kwargs) -> Issue:
        """Create a new issue by calling Jira API to create a new
        issue. A new local reference to the issue is also created.

        :param session: injected ORM session
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
        # translate emails into jira.User objects, if possible
        reporter_kw = kwargs["reporter"]
        watchers_kw = kwargs.get("watchers", [])
        reporter = self.jira.resolve_email(email=reporter_kw) or reporter_kw
        watchers = [self.jira.resolve_email(email=email) for email in watchers_kw]

        # create issue body with Jira markdown format
        body = self.create_message_body(
            template="jira.j2",
            values={
                "author": self.jira.markdown.mention(user=reporter),
                "cc": " ".join(self.jira.markdown.mention(user=w) for w in watchers),
                "body": kwargs["body"],
            },
        )

        # if reporter is not a Jira account, reporter is set to 'Anonymous'
        reporter_id = getattr(reporter, "accountId", None)

        # set defaults
        priority_opt = ["high", "low"]
        priority = (kwargs.get("priority") or "").lower()
        priority = {"name": priority.capitalize()} if priority in priority_opt else None
        labels = kwargs.get("labels", []) + self.configs["default_labels"]

        # create ticket in Jira
        issue = self.jira.create_issue(
            summary=kwargs.get("title"),
            description=body,
            reporter={"id": reporter_id},
            project={"key": self.configs["project_key"]},
            issuetype={"name": self.configs["issue_type"]},
            labels=labels,
            **{"priority": priority} if priority else {},
        )

        # add watchers
        self.jira.add_watchers(issue=issue, watchers=watchers)

        # adding attachments
        for attachment in attachments or []:
            self.jira.add_attachment(issue=issue, attachment=attachment)

        # add new entry to the db
        local_fields = {k: v for k, v in kwargs.items() if k in Issue.__dict__}
        issue = Issue(key=issue.key, **local_fields)

        session.add(issue)
        session.commit()

        logger.info(f"Created issue '{issue.key}'.")

        return self.find_one(key=issue.key)

    @staticmethod
    @with_session
    def get(ticket_id, session=None) -> typing.Optional[Issue]:
        return session.query(Issue).get(ticket_id)

    def find_one(self, **filters) -> typing.Optional[Issue]:
        """Search for a single ticket based on several criteria."""
        return next(iter(self.find_by(limit=1, **filters)), None)

    @with_session
    def find_by(
        self,
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
            query = self.jira.create_jql_query(
                summary=filters.pop("q", None),
                **jira_filters,
            )

            # include additional fields
            fields = fields or []
            if "*navigable" not in fields:
                fields.append("*navigable")
            rendered = "renderedFields" if "rendered" in fields else "fields"

            issues = []  # container for issues result

            jira_issues = self.jira.search_issues(
                jql_str=query,
                maxResults=limit,
                validate_query=False,
                fields=fields,
                expand=rendered,
            )

            for jira_issue in jira_issues:
                issue = self.jira.find_one(key=jira_issue.key, _model=True)

                # prevent cases where local db is not synched with Jira
                # for cases where Jira tickets are not yet locally present
                if issue:
                    issue.jira_issue = jira_issue

                    # add watchers if requested
                    if "watchers" in fields:
                        watchers = self.jira.watchers(jira_issue.key)
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

    @classmethod
    def add_message_to_history(cls, message: O365.Message, model: Issue):
        """Add a message to the issue history."""
        messages_id = model.outlook_messages_id.split(",")
        if message.object_id not in messages_id:
            cls.update(
                issue_id=model.id,
                outlook_messages_id=",".join(messages_id + [message.object_id]),
                updated_at=datetime.datetime.utcnow(),
            )

    def create_comment(
        self,
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
        # translate watchers into jira.User objects iff exists
        watchers = [self.jira.resolve_email(email=email) for email in watchers or []]

        body = self.create_message_body(
            template="jira.j2",
            values={
                "author": self.jira.markdown.mention(user=author),
                "cc": " ".join(
                    self.jira.markdown.mention(user=watcher) for watcher in watchers
                ),
                "body": body,
            },
        )
        self.jira.add_comment(issue=issue, body=body, is_internal=True)

        # add watchers
        self.jira.add_watchers(issue=issue, watchers=watchers)

        # adding attachments
        for attachment in attachments or []:
            self.jira.add_attachment(issue=issue, attachment=attachment)

    @staticmethod
    def create_message_body(template=None, values=None) -> typing.Optional[str]:
        """Create the body of the ticket.

        :param template: the template to build ticket body from
        :param values: values for template interpolation
        """
        if not template:
            return None
        elif not template.endswith(".j2"):
            template = f"{template}.j2"

        templates_path = os.path.join(os.path.dirname(pkg), "templates", "messages")
        loader = jinja2.FileSystemLoader(searchpath=templates_path)
        environ = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return environ.get_template(template).render(**values)
