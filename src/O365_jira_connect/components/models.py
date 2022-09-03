import datetime

from O365_jira_connect.components import db


class AccessToken(db.Model):
    __tablename__ = "access_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token_type = db.Column(db.String, nullable=False)
    scope = db.ARRAY(db.String())
    access_token = db.Column(db.String, nullable=False, unique=True)
    refresh_token = db.Column(db.String, nullable=False, unique=True)
    expires_in = db.Column(db.Integer, nullable=False)
    ext_expires_in = db.Column(db.Integer, nullable=False)
    expires_at = db.Column(db.Float, nullable=False)

    def __str__(self):
        return f"<AccessToken '{self.id}'>"


class Issue(db.Model):
    __tablename__ = "issues"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String, unique=True, nullable=False, index=True)
    outlook_message_id = db.Column(db.String, unique=True)
    outlook_conversation_id = db.Column(db.String, unique=True)
    outlook_messages_id = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    reporter = db.Column(db.String, nullable=False)

    def __str__(self):
        return f"<Issue '{self.key}'>"
