"""
Leaderboard App

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError

from fastapi import FastAPI, HTTPException, status

from .database import Database
from .database.schema import Apps, Leaderboards, Users

app = FastAPI()
db = Database()

@app.get("/apps")
async def getApps():
    """ Get list of apps
    """
    with db.transaction() as store:
        apps = store.query(Apps)
    return apps.all()

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

@app.get("/user/", status_code=status.HTTP_200_OK)
async def getUser(userId: str):
    """ Get user information
    """
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")
        return {'id': user.id, 'nickname': user.nickname}

@app.put("/user/", status_code=status.HTTP_200_OK)
async def updateUser(userId: str, nickname: str):
    """ Update user's nickname
    """
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")
        user.nickname = nickname

@app.delete("/user/", status_code=status.HTTP_200_OK)
async def deleteUser(userId: str):
    """ Delete user from database
    """
    with db.transaction() as store:
        user = store.query(Users).get(userId)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="User not found")
        store.delete(user)

@app.get("/leaderboard/top/", status_code=status.HTTP_200_OK)
async def getTopKScores(appId: str, scoreName: str, k: int):
    """ Get top K scores of an app
    """
    with db.transaction() as store:
        return store.query(Users.nickname, Leaderboards.value) \
                    .join(Users).join(Apps) \
                    .filter(Apps.id == appId, Leaderboards.scoreName == scoreName) \
                    .order_by(Leaderboards.value.desc()) \
                    .limit(k).all()

@app.post("/leaderboard/", status_code=status.HTTP_200_OK)
async def addScore(appId: str, userId: str, scoreName: str, value: int):
    """ Add user score to leaderboard
    """
    with db.transaction() as store:
        leaderboard = Leaderboards(appId=appId, userId=userId, scoreName=scoreName,
                                   value=value)
        store.merge(leaderboard)
