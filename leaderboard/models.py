"""
Pydantic models definitions

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from typing import List
from uuid import UUID

from pydantic import BaseModel


class AppModel(BaseModel):
    """ AppModel class """
    id: UUID
    name: str
    
    class Config:
        """ Config class """
        json_encoders = {UUID: lambda x: x.hex}


class ScoreModel(BaseModel):
    """ ScoreModel class """
    scoreName: str
    value: int


class UserModel(BaseModel):
    """ UserModel class """
    id: str
    nickname: str
    scores: List[ScoreModel]


class TopScoresModel(BaseModel):
    """ TopScoresModel class """
    nickname: str
    value: int

class UserRank(BaseModel):
    """ UserRank class """
    percentile: float
    rank: int
