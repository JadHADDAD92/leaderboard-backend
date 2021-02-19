"""
SQLAlchemy Schema module

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.types import DateTime, Integer, String

from . import Database

Base = declarative_base()

class Users(Base):
    """ SQLAlchemy class for 'users' table
    """
    __tablename__ = "users"
    
    id = Column(UUID(True), primary_key=True)
    nickname = Column(String(30))
    created = Column(DateTime(True), server_default=func.now())


class Apps(Base):
    """ SQLAlchemy class for 'apps' table
    """
    __tablename__ = "apps"
    
    id = Column(UUID(True), server_default=text('uuid_generate_v4()'), primary_key=True)
    name = Column(String(30))


class Leaderboards(Base):
    """ SQLAlchemy class for 'leaderboards' table
    """
    __tablename__ = "leaderboards"
    
    scoreName = Column('score_name', String(30), primary_key=True)
    userId = Column('user_id', ForeignKey(Users.id, ondelete='CASCADE'), primary_key=True)
    appId = Column('app_id', ForeignKey(Apps.id, ondelete='CASCADE'), primary_key=True)
    value = Column(Integer, nullable=False)
    created = Column(DateTime(True), server_default=func.now())
    
    user = relationship(Users)
    app = relationship(Apps)
