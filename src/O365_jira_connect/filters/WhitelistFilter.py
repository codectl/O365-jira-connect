import logging

from O365_jira_connect.filters.base import OutlookMessageFilter

__all__ = ("WhitelistFilter",)

logger = logging.getLogger(__name__)


class WhitelistFilter(OutlookMessageFilter):
    """Filter for message whitelist. It currently checks if the sender's domain is
    whitelisted."""

    def __init__(self, whitelist):
        self.whitelist = whitelist

    def apply(self, message):
        if not message:
            return None

        sender = message.sender.address
        if sender.split("@")[1] not in self.whitelist:
            logger.info(
                f"Message skipped as the sender's email '{sender}' is not whitelisted."
            )
            return None
        return message
