from dataclasses import dataclass

import environs


__all__ = ("Config",)

env = environs.Env()
env.read_env(".env")


@dataclass
class Config:

    # O365 settings
    O365_ID_PROVIDER = env("O365_ID_PROVIDER", "https://login.microsoftonline.com")
    O365_PRINCIPAL = env("O365_PRINCIPAL", None)
    O365_TENANT_ID = env("O365_TENANT_ID", None)
    O365_CLIENT_ID = env("O365_CLIENT_ID", None)
    O365_CLIENT_SECRET = env("O365_CLIENT_SECRET", None)
    O365_SCOPES = env.list("O365_SCOPES", [])

    # Jira settings
    JIRA_PLATFORM_URL = env("JIRA_PLATFORM_URL", "https://atlassian.net")
    JIRA_PLATFORM_USER = env("JIRA_PLATFORM_USER", None)
    JIRA_PLATFORM_TOKEN = env("JIRA_PLATFORM_TOKEN", None)
    JIRA_ISSUE_TYPE = env("JIRA_ISSUE_TYPE", "Task")
    JIRA_ISSUE_DEFAULT_LABELS = env.list("JIRA_ISSUE_DEFAULT_LABELS", [])

    # Streaming connection settings
    # See https://bit.ly/3eqDsGs for details
    CONNECTION_TIMEOUT_IN_MINUTES = env.int("CONNECTION_TIMEOUT_IN_MINUTES", 120)
    KEEP_ALIVE_INTERVAL_IN_SECONDS = env.int("KEEP_ALIVE_INTERVAL_IN_SECONDS", 300)

    # Filter settings
    EMAIL_WHITELISTED_DOMAINS = env.list("EMAIL_WHITELISTED_DOMAINS", [])
    EMAIL_BLACKLIST = env.list("EMAIL_BLACKLIST", [])
