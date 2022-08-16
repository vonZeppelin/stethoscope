import sys
import oracledb

from sqlalchemy import Column, DateTime, Integer, Unicode, UnicodeText, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


# https://levelup.gitconnected.com/using-python-oracledb-1-0-with-sqlalchemy-pandas-django-and-flask-5d84e910cb19
oracledb.version = "8.3.0"
sys.modules["cx_Oracle"] = oracledb

Base = declarative_base()


class Video(Base):
    __tablename__ = "video"

    id = Column(Unicode(11), primary_key=True)
    title = Column(Unicode(100), nullable=False)
    description = Column(UnicodeText, nullable=False)
    published = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False)
    thumbnail_url = Column(UnicodeText, nullable=True)


def create_session(user: str, password: str, dsn: str) -> sessionmaker:
    engine = create_engine(
        f"oracle://{user}:{password}@",
        connect_args={"dsn": dsn},
        max_identifier_length=128
    )

    Base.metadata.create_all(engine)

    return sessionmaker(engine)
