import logging

from O365_jira_connect.filters.base import OutlookMessageFilter
from O365_jira_connect.services.issue import issue_s

__all__ = ("ValidateMetadataFilter",)

logger = logging.getLogger(__name__)


class ValidateMetadataFilter(OutlookMessageFilter):
    """Filter message based on metadata present in the message"""

    def apply(self, message):
        if not message:
            return None

        soup = message.get_body_soup()

        if soup is None or soup.head is None:
            return message
        else:

            # append message to history if jira metadata is present
            opts = {"outlook_conversation_id": message.conversation_id, "_model": True}
            model = issue_s.find_one(**opts)

            # ignore the notification email sent to user after the creation of an issue
            if soup.head.find("meta", attrs={"content": "jira issue notification"}):
                issue_s.add_message_to_history(message, model=model)
                logger.info(
                    "Message filtered as this is a message notification to the user "
                    "about created issue."
                )
                return None

            # ignore the message sent when a new comment is added to the issue
            elif soup.head.find("meta", attrs={"content": "relay jira comment"}):
                IssueSvc.add_message_to_history(message, model=model)
                logger.info(
                    "Message filtered as this is a relay message from a Jira comment."
                )
                return None
            else:
                return message
