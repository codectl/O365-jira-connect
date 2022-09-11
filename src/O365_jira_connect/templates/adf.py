import os

import jinja2
import jira
import pyadf

__all__ = ("TemplateBuilder",)


class TemplateBuilder:
    """Create template messages out of jinja2 templates
    and Atlassian Document Format. See https://bit.ly/3eJhy3G
    for documentation
    """

    def __init__(self):
        templates_path = os.path.join(os.path.dirname(__file__), "j2")
        loader = jinja2.FileSystemLoader(searchpath=templates_path)
        self.env = jinja2.Environment(
            loader=loader,
            autoescape=jinja2.select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template, **values):
        if not template:
            return None
        elif not template.endswith(".j2"):
            template = f"{template}.j2"

        return self.env.get_template(template).render(**values)

    @classmethod
    def jira_issue_body(cls, author, cc=(), body=None):
        doc = pyadf.Document().paragraph().text("From: ")
        doc = cls._resolve_mention(doc, user=author).hardbreak()
        if cc:
            doc = doc.text("Cc: ")
            for user in cc:
                doc = cls._resolve_mention(doc, user=user)
        doc = doc.end()
        doc.paragraph().text(body)
        return doc.to_doc()

    def outlook_message_reply_body(self, **values):
        return self.wrap_text(text=self.render("reply", **values))

    @staticmethod
    def wrap_text(text):
        return pyadf.Document().paragraph().text(text).to_doc()

    @staticmethod
    def _resolve_mention(node: pyadf.Paragraph, user) -> pyadf.Paragraph:
        if isinstance(user, jira.User):
            return node.mention(mention_id=user.accountId,
                                mention_text=user.displayName)
        elif isinstance(user, str):
            return node.link(href=user)
        else:
            return node
