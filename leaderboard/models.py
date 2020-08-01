"""
Pydantic models definitions

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from typing import List
from uuid import UUID

from pydantic import BaseModel


class AppModel(BaseModel):
    id: UUID
    name: str
    
    class Config:
        json_encoders = {UUID: lambda x: x.hex}


class ScoreModel(BaseModel):
    scoreName: str
    value: int


class UserModel(BaseModel):
    id: str
    nickname: str
    scores: List[ScoreModel]


class TopScoresModel(BaseModel):
    nickname: str
    value: int
