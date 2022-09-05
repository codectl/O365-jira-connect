import logging

from O365_jira_connect.filters.base import OutlookMessageFilter

__all__ = ("SenderWhitelistFilter",)

logger = logging.getLogger(__name__)


class SenderWhitelistFilter(OutlookMessageFilter):
    """Filter for message whose sender is whitelisted. It currently checks for the
    sender's domain."""

    def __init__(self, whitelisted):
        self.whitelisted = whitelisted

    def apply(self, message):
        if not message:
            return None

        sender = message.sender.address
        if sender.split("@")[1] not in self.whitelisted:
            logger.info(
                f"Message skipped as the sender's email '{sender}' is not whitelisted."
            )
            return None
        return message
