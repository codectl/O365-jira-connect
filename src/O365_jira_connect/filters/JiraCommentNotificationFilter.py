import functools
import logging
import re

import requests
import O365.mailbox

from O365_jira_connect import utils
from O365_jira_connect.services import IssueSvc, JiraSvc
from O365_jira_connect.filters.base import OutlookMessageFilter
from O365_jira_connect.handlers import JiraNotificationHandler

logger = logging.getLogger(__name__)


class JiraCommentNotificationFilter(OutlookMessageFilter):
    """Filter for messages that represent comments added to issues. The email
    recipient gets notified whenever a new comment has been added to the issue.
    """

    def __init__(self, folder: O365.mailbox.Folder):
        self.folder = folder

    def apply(self, message):
        if not message:
            return None

        if message.sender.address.split("@")[1] == "automation.atlassian.com":
            svc = JiraSvc()

            # load message json payload
            payload = utils.message_json(message)

            model = IssueSvc.find_one(key=payload["issue"], _model=True)
            if not model:
                logger.warning("Comment on issue that was not found.")
                return None

            # locate last lent message to reply on
            last_message_id = model.outlook_messages_id.split(",")[-1]
            try:
                last_message = self.folder.get_message(object_id=last_message_id)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == requests.codes.not_found:
                    logger.warning("Reply-to message was not found; no email was sent.")
            else:

                # locate the specific comment given the
                comment = svc.comment(
                    issue=payload["issue"],
                    comment=payload["id"],
                    expand="renderedBody",
                )

                # embed base64 images under RFC2397
                scheme = "data:image/jpeg;base64"
                encode = utils.encode_content
                data = functools.partial(svc.content, base="{server}{path}")
                body = re.sub(
                    pattern=r'src="(.*?)"',
                    repl=lambda m: f"src='{scheme},{encode(data(path=m.group(1)))}'",
                    string=comment.renderedBody,
                )

                # send out the comment message has a reply to the last sent message
                metadata = {"name": "message", "content": "relay jira comment"}
                reply = JiraNotificationHandler.create_reply(
                    message=last_message,
                    values={
                        "body": body,
                        "author": payload["author"]["name"],
                        "metadata": [metadata],
                    },
                )
                reply.send()

            # delete message since it serves no further purpose
            message.delete()

            return None

        return message
