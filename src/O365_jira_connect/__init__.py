from importlib import metadata
from .cli import cli

__all__ = (cli,)
__version__ = metadata.version("O365-jira-connect")
