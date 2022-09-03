import logging
import typing

from O365.utils import BaseTokenBackend

from O365_jira_connect.components import db
from O365_jira_connect.components.models import AccessToken

logger = logging.getLogger(__name__)


class DatabaseTokenBackend(BaseTokenBackend):

    def __init__(self):
        super().__init__()
        self.svc = TokenSvc()

    def load_token(self):
        return self.svc.find_by(one=True)

    def save_token(self):
        if self.token is None:
            raise ValueError("You have to set the 'token' first.")

        # replace older token
        token = self.svc.find_by(one=True)
        if token is not None:
            self.svc.delete(token_id=token.id)

        # ... with the new one
        self.svc.create(**self.token)

        return True

    def delete_token(self):
        if self.token is None:
            return False

        token = self.svc.find_by(one=True, access_token=self.token.access_token)
        if token is not None:
            self.svc.delete(token_id=token.id)

        return False

    def check_token(self):
        return self.svc.find_by(one=True) is not None


class TokenSvc:
    @staticmethod
    def create(**kwargs) -> AccessToken:
        token = AccessToken(**kwargs)

        db.session.add(token)
        db.session.commit()

        logger.debug(f"Created token '{token.access_token}'.")

        return token

    @staticmethod
    def get(token_id) -> typing.Optional[AccessToken]:
        return AccessToken.query.get(token_id)

    @staticmethod
    def find_by(
        one=False, **filters
    ) -> typing.Union[list[AccessToken], typing.Optional[AccessToken]]:
        query = AccessToken.query.filter_by(**filters)
        return query.all() if not one else query.one_or_none()

    @classmethod
    def update(cls, token_id, **kwargs):
        token = cls.get(token_id=token_id)
        for key, value in kwargs.items():
            if hasattr(token, key):
                setattr(token, key, value)
        db.session.commit()

        access_token = token.access_token
        msg = f"Updated token '{access_token}' with the attributes: '{kwargs}'."
        logger.info(msg)

    @classmethod
    def delete(cls, token_id):
        token = cls.get(token_id=token_id)
        if token:
            db.session.delete(token)
            db.session.commit()

            logger.debug(f"Deleted token '{token.access_token}'.")
