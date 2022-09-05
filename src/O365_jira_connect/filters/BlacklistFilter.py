import logging

from O365_jira_connect.filters.base import OutlookMessageFilter

__all__ = ("BlacklistFilter",)

logger = logging.getLogger(__name__)


class BlacklistFilter(OutlookMessageFilter):
    """Filter for message blacklist. It currently checks if sender's email is
    blacklisted."""

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
