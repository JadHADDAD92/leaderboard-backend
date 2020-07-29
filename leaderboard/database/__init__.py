"""
SQLAlchemy database setup module

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = os.environ['DATABASE_URL']

class Singleton(type):
    """ singleton pattern
    """
    def __init__(cls, name, bases, dict_):
        super().__init__(name, bases, dict_)
        cls._instance = None
    
    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class Database(metaclass=Singleton):
    """ main database object
    """
    def __init__(self, uri=SQLALCHEMY_DATABASE_URL):
        """ connect to SQLAlchemy database
        """
        self.engine = create_engine(uri, pool_timeout=0)
    
    @contextmanager
    def transaction(self):
        """ execute a SQL transaction
        """
        session = sessionmaker(bind=self.engine)()
        try:
            yield session
            session.commit()
        except:
            session.rollback()
            raise
        finally:
            session.close()
