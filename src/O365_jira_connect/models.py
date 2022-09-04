import datetime

import jira.resources
from sqlalchemy import ARRAY, Column, DateTime, Float, Integer, String

from O365_jira_connect.components import Base


class AccessToken(Base):
    __tablename__ = "access_tokens"

    id = Column(Integer, primary_key=True)
    token_type = Column(String, nullable=False)
    scope = ARRAY(String())
    access_token = Column(String, nullable=False, unique=True)
    refresh_token = Column(String, nullable=True, unique=True)
    expires_in = Column(Integer, nullable=False)
    ext_expires_in = Column(Integer, nullable=False)
    expires_at = Column(Float, nullable=False)

    def __str__(self):
        return f"<AccessToken '{self.id}'>"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False, index=True)
    outlook_message_id = Column(String, unique=True)
    outlook_conversation_id = Column(String, unique=True)
    outlook_messages_id = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)
    reporter = Column(String, nullable=False)
    jira_issue: jira.resources.Issue = None  # a reference to Jira issue

    def __str__(self):
        return f"<Issue '{self.key}'>"
