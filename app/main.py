"""
Leaderboard App

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from datetime import datetime
from hashlib import sha1
from os import environ
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .database import Database
from .database.schema import Apps, Leaderboards, Users
from .models import CreateUser, TopScoresResponseModel, UserModel, UserRank
from .strings import (APP_NOT_FOUND, CHECKSUM_MISMATCH, NO_CHECKSUM,
                      SCORENAME_NOT_FOUND, USER_ALREADY_REGISTERED,
                      USER_NOT_FOUND)

production = environ.get('SERVER_TYPE', 'production') == 'production'

if production:
    docsURL = None
    redocURL = None
else:
    docsURL = "/docs"
    redocURL = "/redoc"

app = FastAPI(docs_url=docsURL, redoc_url=redocURL)

def computeChecksum(**kwargs):
    """ Compute checksum for parameters
    """
    concat = ""
    for key in sorted(kwargs):
        concat += key
        value = kwargs[key]
        if value is not None:
            concat += str(kwargs[key])
    concat += environ.get('APP_SECRET')
    return sha1(concat.encode()).hexdigest()

def validateParameters(**kwargs):
    """ Validate parameters checksum
    """
    checksum = kwargs.pop('checksum')
    
    if checksum is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=NO_CHECKSUM)
    if checksum != computeChecksum(**kwargs):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=CHECKSUM_MISMATCH)

@app.post("/user", response_model=CreateUser, status_code=status.HTTP_201_CREATED)
def createUser(userId: str, nickname: Optional[str]=None, checksum: str=Header(None),
               db=Depends(Database)):
    """ Create user in database
    """
    validateParameters(userId=userId, nickname=nickname, checksum=checksum)
    if nickname in ('', None):
        nickname = f"user_{str(datetime.utcnow().timestamp()).split('.')[1]}"
    try:
        with db.transaction() as store:
            user = Users(id=userId, nickname=nickname)
            store.add(user)
            store.flush()
            store.expunge(user)
    except IntegrityError:
        raise HTTPException(status_code=401, detail=USER_ALREADY_REGISTERED)
    else:
        return {'nickname': user.nickname}

@app.get("/user", response_model=UserModel)
def getUser(appId: str, userId: str, checksum: str=Header(None), db=Depends(Database)):
    """ Get user information
    """
    validateParameters(appId=appId, userId=userId, checksum=checksum)
    with db.transaction() as store:
        appDB = store.query(Apps).get(appId)
        if appDB is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=APP_NOT_FOUND)
        user = store.query(Users).get(userId)
        scores = store.query(Leaderboards.scoreName, Leaderboards.value) \
                      .filter_by(userId=userId, appId=appId) \
                      .all()
        scores = list(map(lambda x: x._asdict(), scores))
        return {'id': userId, 'nickname': user.nickname, 'scores': scores}

@app.get("/user/rank", response_model=UserRank)
def getUserRank(appId: str, scoreName: str, userId: str, checksum: str=Header(None),
                db=Depends(Database)):
    """ Get user rank in percentage in a specific score name
    """
    validateParameters(appId=appId, scoreName=scoreName, userId=userId, checksum=checksum)
    with db.transaction() as store:
        appDB = store.query(Apps).get(appId)
        if appDB is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=APP_NOT_FOUND)
        
        scoreNames = store.query(Leaderboards.scoreName) \
                          .filter_by(appId=appId) \
                          .distinct()
        scoreNames = [val for (val, ) in scoreNames]
        if scoreName not in scoreNames:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=SCORENAME_NOT_FOUND)
        
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
        if scoresCount == 1:
            percentile = 100
            rank = 1
        else:
            percentile = (lowerScores * 100) // (scoresCount - 1)
            rank = scoresCount - lowerScores
        
        return {
            'percentile': percentile,
            'rank': rank
        }

@app.put("/user")
def updateUser(nickname: str, userId: str, checksum: str=Header(None),
               db=Depends(Database)):
    """ Update user's nickname
    """
    validateParameters(userId=userId, nickname=nickname, checksum=checksum)
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        user.nickname = nickname
        store.merge(user)

@app.delete("/user")
def deleteUser(userId: str, checksum: str=Header(None), db=Depends(Database)):
    """ Delete user from database
    """
    validateParameters(userId=userId, checksum=checksum)
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is not None:
            store.delete(user)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=USER_NOT_FOUND)

@app.get("/leaderboard/top", response_model=TopScoresResponseModel)
def getTopKScores(appId: str, userId: str, scoreName: str, k: int,
                  checksum: str=Header(None), db=Depends(Database)):
    """ Get top K scores of an app
    """
    validateParameters(appId=appId, userId=userId, scoreName=scoreName, k=k,
                       checksum=checksum)
    with db.transaction() as store:
        topScores = store.query(Users.nickname, Leaderboards.value) \
                         .join(Users).join(Apps) \
                         .filter(Apps.id == appId, Leaderboards.scoreName == scoreName) \
                         .order_by(Leaderboards.value.desc()) \
                         .limit(k)
        userScore = store.query(Leaderboards) \
                         .join(Users).join(Apps) \
                         .filter(Apps.id == appId, Leaderboards.scoreName == scoreName) \
                         .filter(Users.id == userId) \
                         .one_or_none()
        
        userRankChecksum = computeChecksum(appId=appId, userId=userId,
                                           scoreName=scoreName)
        userRank = getUserRank(appId, scoreName, userId, userRankChecksum, db)
        rank = userRank['rank']
        return {
            'scores': list(map(lambda x: x._asdict(), topScores.all())),
            'userScore': userScore.value if userScore is not None else 0,
            'userRank': rank if rank is not None else -1
        }

@app.post("/leaderboard", response_model=UserRank)
def addScore(appId: str, scoreName: str, value: int, userId: str,
             checksum: str=Header(None), db=Depends(Database)):
    """ Add user score to leaderboard
    """
    validateParameters(appId=appId, scoreName=scoreName, value=value, userId=userId,
                       checksum=checksum)
    with db.transaction() as store:
        leaderboard = Leaderboards(appId=appId, userId=userId, scoreName=scoreName,
                                   value=value)
        store.merge(leaderboard)
        
        store.commit()
        userRankChecksum = computeChecksum(appId=appId, userId=userId,
                                           scoreName=scoreName)
        return getUserRank(appId, scoreName, userId, userRankChecksum, db)

@app.delete("/leaderboard")
def deleteScore(appId: str, scoreName: str, userId: str, checksum: str=Header(None),
                db=Depends(Database)):
    """ Delete user score from leaderboard
    """
    validateParameters(appId=appId, scoreName=scoreName, userId=userId, checksum=checksum)
    with db.transaction() as store:
        score = store.query(Leaderboards) \
                     .filter_by(appId=appId, userId=userId, scoreName=scoreName) \
                     .one_or_none()
        if score is not None:
            store.delete(score)
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=SCORENAME_NOT_FOUND)
