import logging

from O365_jira_connect.filters.base import OutlookMessageFilter

__all__ = ("SenderBlacklistFilter",)

logger = logging.getLogger(__name__)


class SenderBlacklistFilter(OutlookMessageFilter):
    """Filter for message whose sender is not blacklisted. It currently checks for
    sender's email."""

    def __init__(self, blacklist):
        self.blacklist = blacklist

    def apply(self, message):
        if not message:
            return None

        sender = message.sender.address
        if sender in self.blacklist:
            logger.info(
                f"Message skipped as the sender's email '{sender}' is blacklisted."
            )
            return None
        return message
