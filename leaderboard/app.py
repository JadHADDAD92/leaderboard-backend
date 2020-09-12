"""
Leaderboard App

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from .database import Database
from .database.schema import Apps, Leaderboards, Users
from .models import TopScoresModel, UserModel, UserRank, CreateUser

app = FastAPI()
db = Database()

def validateUser(userToken: str=Header(None)):
    """ Validate user token
    """
    if userToken is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Unauthorized access")
    with db.transaction() as store:
        user = store.query(Users).filter_by(token=userToken).one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Invalid token")
        store.expunge(user)
    return user

@app.post("/user/", response_model=CreateUser, status_code=status.HTTP_201_CREATED)
async def createUser(userId: str, nickname: Optional[str]=None):
    """ Create user in database
    """
    if nickname is None:
        nickname = f"user_{datetime.utcnow().timestamp()}"
    user = Users(id=userId, nickname=nickname)
    try:
        with db.transaction() as store:
            store.add(user)
            store.flush()
            store.expunge(user)
    except IntegrityError:
        raise HTTPException(status_code=401, detail="User already registered")
    else:
        return {'nickname': user.nickname, 'token': user.token}

@app.get("/user/", response_model=UserModel)
async def getUser(appId: str, user: Users = Depends(validateUser)):
    """ Get user information
    """
    with db.transaction() as store:
        appDB = store.query(Apps).get(appId)
        if appDB is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="App not found")
        scores = store.query(Leaderboards.scoreName, Leaderboards.value) \
                      .filter_by(userId=user.id, appId=appId) \
                      .all()
        scores = list(map(lambda x: x._asdict(), scores))
        return {'id': user.id, 'nickname': user.nickname, 'scores': scores}

@app.get("/user/rank", response_model=UserRank)
async def getUserRank(appId: str, scoreName, user: Users = Depends(validateUser)):
    """ Get user rank in percentage in a specific score name
    """
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
                         .filter_by(userId=user.id, appId=appId, scoreName=scoreName)
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
async def updateUser(nickname: str, user: Users = Depends(validateUser)):
    """ Update user's nickname
    """
    with db.transaction() as store:
        user.nickname = nickname
        store.merge(user)

@app.delete("/user/")
async def deleteUser( user: Users = Depends(validateUser)):
    """ Delete user from database
    """
    with db.transaction() as store:
        store.delete(user)

@app.get("/leaderboard/top/", response_model=List[TopScoresModel],
         dependencies=[Depends(validateUser)])
async def getTopKScores(appId: str, scoreName: str, k: int):
    """ Get top K scores of an app
    """
    with db.transaction() as store:
        topScores = store.query(Users.nickname, Leaderboards.value) \
                         .join(Users).join(Apps) \
                         .filter(Apps.id == appId, Leaderboards.scoreName == scoreName) \
                         .order_by(Leaderboards.value.desc()) \
                         .limit(k)
        return list(map(lambda x: x._asdict(), topScores.all()))

@app.post("/leaderboard/", response_model=UserRank)
async def addScore(appId: str, scoreName: str, value: int,
                   user: Users = Depends(validateUser)):
    """ Add user score to leaderboard
    """
    with db.transaction() as store:
        userId = user.id
        leaderboard = Leaderboards(appId=appId, userId=userId, scoreName=scoreName,
                                   value=value)
        store.merge(leaderboard)
        
        return getUserRank(appId, scoreName, userId)

@app.delete("/leaderboard/")
async def deleteScore(appId: str, scoreName: str, user: Users = Depends(validateUser)):
    """ Delete user score from leaderboard
    """
    with db.transaction() as store:
        score = store.query(Leaderboards) \
                     .filter_by(appId=appId, userId=user.id, scoreName=scoreName) \
                     .one_or_none()
        store.delete(score)
