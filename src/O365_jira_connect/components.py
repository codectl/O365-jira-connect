from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()
Session = sessionmaker()


def init_engine(engine_url, debug=False):
    engine = create_engine(url=engine_url, echo=debug)
    Session.configure(bind=engine)
    Base.metadata.create_all(bind=engine)


def with_session(f):
    """Create session for given function."""
    def wrapper(*args, **kwargs):
        session = Session()
        session.begin()
        f(*args, session=session, **kwargs)
        session.close()
    return wrapper
