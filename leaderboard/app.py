"""
Leaderboard App

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, status
from sqlalchemy.exc import IntegrityError

from .models import AppModel, UserModel, TopScoresModel
from .database import Database
from .database.schema import Apps, Leaderboards, Users

app = FastAPI()
db = Database()

@app.get("/apps", response_model=List[AppModel])
async def getApps():
    """ Get list of apps
    """
    with db.transaction() as store:
        apps = store.query(Apps.id, Apps.name)
    return list(map(lambda x: x._asdict(), apps.all()))

@app.post("/user/", status_code=status.HTTP_201_CREATED)
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
        return {'nickname': user.nickname}

@app.get("/user/", response_model=UserModel)
async def getUser(userId: str, appId: str):
    """ Get user information
    """
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")
        appDB = store.query(Apps).get(appId)
        if appDB is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="App not found")
        scores = store.query(Leaderboards.scoreName, Leaderboards.value) \
                      .filter_by(userId=userId, appId=appId) \
                      .all()
        scores = list(map(lambda x: x._asdict(), scores))
        return {'id': user.id, 'nickname': user.nickname, 'scores': scores}

@app.put("/user/")
async def updateUser(userId: str, nickname: str):
    """ Update user's nickname
    """
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")
        user.nickname = nickname

@app.delete("/user/")
async def deleteUser(userId: str):
    """ Delete user from database
    """
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")
        store.delete(user)

@app.get("/leaderboard/top/", response_model=List[TopScoresModel])
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

@app.post("/leaderboard/")
async def addScore(appId: str, userId: str, scoreName: str, value: int):
    """ Add user score to leaderboard
    """
    with db.transaction() as store:
        leaderboard = Leaderboards(appId=appId, userId=userId, scoreName=scoreName,
                                   value=value)
        store.merge(leaderboard)
