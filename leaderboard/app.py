"""
Leaderboard App

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from datetime import datetime
from hashlib import sha1
from os import environ
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .database import Database
from .database.schema import Apps, Leaderboards, Users
from .models import TopScoresModel, UserModel, UserRank

app = FastAPI()
db = Database()

def validateParameters(*args, **kwargs):
    """ Validate parameters checksum
    """
    checksum = kwargs.pop('checksum')
    
    if checksum is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized access: no checksum")
    concat = ""
    for key in sorted(kwargs):
        concat += key
        value = kwargs[key]
        if value is not None:
            concat += kwargs[key]
    concat += environ.get('APP_SECRET')
    if checksum != sha1(concat.encode()).hexdigest():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized access: checksum mismatch")

@app.post("/user/", status_code=status.HTTP_201_CREATED)
async def createUser(userId: str, nickname: Optional[str]=None,
                     checksum: str=Header(None)):
    """ Create user in database
    """
    validateParameters(userId=userId, nickname=nickname, checksum=checksum)
    if nickname is None:
        nickname = f"user_{datetime.utcnow().timestamp()}"
    try:
        with db.transaction() as store:
            user = Users(id=userId, nickname=nickname)
            store.add(user)
            store.flush()
            store.expunge(user)
    except IntegrityError:
        raise HTTPException(status_code=401, detail="User already registered")
    else:
        return {'nickname': user.nickname}

@app.get("/user/", response_model=UserModel)
async def getUser(appId: str, userId: str, checksum: str=Header(None)):
    """ Get user information
    """
    validateParameters(appId=appId, userId=userId, checksum=checksum)
    with db.transaction() as store:
        appDB = store.query(Apps).get(appId)
        if appDB is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="App not found")
        user = store.query(Users).get(userId)
        scores = store.query(Leaderboards.scoreName, Leaderboards.value) \
                      .filter_by(userId=userId, appId=appId) \
                      .all()
        scores = list(map(lambda x: x._asdict(), scores))
        return {'id': userId, 'nickname': user.nickname, 'scores': scores}

@app.get("/user/rank", response_model=UserRank)
async def getUserRank(appId: str, scoreName: str, userId: str, checksum: str=Header(None)):
    """ Get user rank in percentage in a specific score name
    """
    validateParameters(appId=appId, scoreName=scoreName, userId=userId, checksum=checksum)
    with db.transaction() as store:
        appDB = store.query(Apps).get(appId)
        if appDB is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="App not found")
        
        scoreNames = store.query(Leaderboards.scoreName) \
                          .filter_by(appId=appId) \
                          .distinct()
        scoreNames = [val for (val, ) in scoreNames]
        if scoreName not in scoreNames:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Score name not found")
        
        userScore = store.query(Leaderboards.value) \
                         .filter_by(userId=userId, appId=appId, scoreName=scoreName)
        lowerScores = store.query(func.count(Leaderboards.value)) \
                           .filter(Leaderboards.value < userScore,
                                   Leaderboards.appId == appId,
                                   Leaderboards.scoreName == scoreName) \
                           .scalar()
        scoresCount = store.query(func.count(Leaderboards.value)) \
                           .filter_by(appId=appId, scoreName=scoreName) \
                           .scalar()
        
        return {
            'percentile': (lowerScores * 100) // (scoresCount - 1),
            'rank': scoresCount - lowerScores
        }

@app.put("/user/")
async def updateUser(nickname: str, userId: str, checksum: str=Header(None)):
    """ Update user's nickname
    """
    validateParameters(userId=userId, nickname=nickname, checksum=checksum)
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        user.nickname = nickname
        store.merge(user)

@app.delete("/user/")
async def deleteUser(userId: str, checksum: str=Header(None)):
    """ Delete user from database
    """
    validateParameters(userId=userId, checksum=checksum)
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        store.delete(user)

@app.get("/leaderboard/top/", response_model=List[TopScoresModel])
async def getTopKScores(appId: str, scoreName: str, k: int, checksum: str=Header(None)):
    """ Get top K scores of an app
    """
    validateParameters(appId=appId, scoreName=scoreName, k=k, checksum=checksum)
    with db.transaction() as store:
        topScores = store.query(Users.nickname, Leaderboards.value) \
                         .join(Users).join(Apps) \
                         .filter(Apps.id == appId, Leaderboards.scoreName == scoreName) \
                         .order_by(Leaderboards.value.desc()) \
                         .limit(k)
        return list(map(lambda x: x._asdict(), topScores.all()))

@app.post("/leaderboard/", response_model=UserRank)
async def addScore(appId: str, scoreName: str, value: int, userId: str,
                   checksum: str=Header(None)):
    """ Add user score to leaderboard
    """
    validateParameters(appId=appId, scoreName=scoreName, value=value, userId=userId,
                       checksum=checksum)
    with db.transaction() as store:
        leaderboard = Leaderboards(appId=appId, userId=userId, scoreName=scoreName,
                                   value=value)
        store.merge(leaderboard)
        

        return getUserRank(appId, scoreName, userId)
