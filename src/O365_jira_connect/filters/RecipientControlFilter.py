import itertools
import logging

import O365.mailbox

from O365_jira_connect.filters.base import OutlookMessageFilter
from O365_jira_connect.services.issue import issue_s

__all__ = ("RecipientControlFilter",)

logger = logging.getLogger(__name__)


class RecipientControlFilter(OutlookMessageFilter):
    """Filter for message validating its recipients"""

    def __init__(self, email, ignore: list[O365.mailbox.Folder] = ()):
        self.email = email
        self.ignore = ignore

    def apply(self, message):
        if not message:
            return None

        # exclude case where recipient is both present in the 'from' recipient field
        # and in any of the other recipient fields. This case will cause a duplicate
        # notification. Therefore, exclude the event where the message is sent because
        # the event will be triggered upon message delivery.
        other_recipients = itertools.chain(
            (e.address for e in message.cc),
            (e.address for e in message.bcc),
            (e.address for e in message.to),
        )
        if (
            self.email == message.sender.address
            and self.email in other_recipients
            and any(comp.folder_id == message.folder_id for comp in self.ignore)
        ):
            logger.info("Message filtered as the notification is a duplicate.")
            return None

        # check for existing issue
        cid = message.conversation_id
        existing_issue = issue_s.find_one(outlook_conversation_id=cid, _model=True)

        if not existing_issue:
            # exclude if new message initiated by the recipient
            if self.email == message.sender.address:
                logger.info(
                    f"Message filtered as the recipient '{self.email}' "
                    "is the sender of a new conversation."
                )
                return None

            # exclude if new message did not come from the recipient
            # and is not directly sent 'to' recipient (must be in cc or bcc)
            elif self.email not in (e.address for e in message.to):
                logger.info(
                    f"Message filtered as the recipient '{self.email}' "
                    "is not in the senders list of a new conversation."
                )
                return None

        return message
