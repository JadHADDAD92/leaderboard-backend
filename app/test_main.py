"""
Unit tests using PyTest

@author: Jad Haddad <jad.haddad92@gmail.com> 2020
"""
from uuid import uuid4

from fastapi.testclient import TestClient

from .database import Database
from .database.schema import Base, Apps, Users, Leaderboards
from .main import app, computeChecksum

SQLALCHEMY_DATABASE_URL = "postgresql://postgres:secretpassword@db:5432/testtreederboards"

class DatabaseTest(Database):
    def __init__(self, uri: str=SQLALCHEMY_DATABASE_URL):
        """ connect to SQLAlchemy database
        """
        super().__init__(uri)

app.dependency_overrides[Database] = DatabaseTest

client = TestClient(app)

appId = uuid4().hex
userId = "userIdTest"
scoreName = "arcade"

def test_recreate_database():
    engine = DatabaseTest().engine
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    with DatabaseTest().transaction() as store:
        apps = store.query(Apps).all()
        users = store.query(Users).all()
        leaderboards = store.query(Leaderboards).all()
    assert apps == []
    assert users == []
    assert leaderboards == []

def test_create_user():
    def _createUser(userId, nickname=None, noChecksum=False, wrongChecksum=False):
        if nickname is None:
            nickname = ""
        checksum = computeChecksum(userId=userId, nickname=nickname)
        
        if wrongChecksum:
            params = {"userId": userId, "nickname": f"{nickname}ergerg"}
        else:
            params = {"userId": userId, "nickname": nickname}
        
        if noChecksum:
            return client.post("/user", params=params)
        else:
            return client.post("/user", params=params, headers={"checksum": checksum})
    
    response = _createUser(userId="userIdTest", nickname="testNickname", noChecksum=True)
    assert response.status_code == 401
    assert response.json() == {'detail': 'Unauthorized access: no checksum'}
    
    response = _createUser(userId="userIdTest", nickname="testNickname", wrongChecksum=True)
    assert response.status_code == 401
    assert response.json() == {'detail': 'Unauthorized access: checksum mismatch'}
    
    response = _createUser(userId="userIdTest", nickname="testNickname")
    assert response.status_code == 201
    assert response.json() == {"nickname":"testNickname"}
    
    response = _createUser(userId="userIdTest2")
    assert response.status_code == 201
    
    response = _createUser(userId="userIdTest", nickname="testNickname")
    assert response.status_code == 401
    assert response.json() == {"detail":"User already registered"}

def test_update_user():
    newNickname = "testNickname2"
    checksum = computeChecksum(userId=userId, nickname=newNickname)
    params = {"userId": userId, "nickname": newNickname}
    response = client.put("/user", params=params, headers={"checksum": checksum})
    assert response.status_code == 200

def test_create_app():
    with DatabaseTest().transaction() as store:
        app = Apps(id=appId, name="Twype")
        store.add(app)
        store.flush()

def test_get_user():
    checksum = computeChecksum(userId=userId, appId=appId)
    params = {"userId": userId, "appId": appId}
    response = client.get("/user", params=params, headers={"checksum": checksum})
    expectedResponse = {'id': 'userIdTest', 'nickname': 'testNickname2', 'scores': []}
    assert response.status_code == 200
    assert response.json() == expectedResponse
    
    params = {"userId": "", "appId": appId}
    checksum = computeChecksum(userId="", appId=appId)
    response = client.get("/user", params=params, headers={"checksum": checksum})
    assert response.status_code == 404
    assert response.json() == {'detail': 'User not found'}
    
    params = {"userId": userId, "appId": uuid4().hex}
    checksum = computeChecksum(userId=userId, appId=params['appId'])
    response = client.get("/user", params=params, headers={"checksum": checksum})
    assert response.status_code == 404
    assert response.json() == {'detail': 'App not found'}

def test_add_score():
    def _addScore(scoreName, value):
        checksum = computeChecksum(userId=userId, appId=appId, scoreName=scoreName,
                                   value=value)
        params = {"userId": userId, "appId": appId, "scoreName": scoreName,
                  "value": value}
        return client.post("/leaderboard", params=params, headers={"checksum": checksum})
    response = _addScore(scoreName=scoreName, value=120)
    assert response.status_code == 200

def test_user_rank():
    checksum = computeChecksum(userId=userId, appId=appId, scoreName=scoreName)
    params = {"userId": userId, "appId": appId, "scoreName": scoreName}
    response = client.get("/user/rank", params=params, headers={"checksum": checksum})
    assert response.status_code == 200
    assert response.json() == {'percentile': 100, 'rank': 1}
    
    params = {"userId": userId, "appId": uuid4().hex, "scoreName": scoreName}
    checksum = computeChecksum(userId=userId, appId=params['appId'], scoreName=scoreName)
    response = client.get("/user/rank", params=params, headers={"checksum": checksum})
    assert response.status_code == 404
    assert response.json() == {'detail': 'App not found'}
    
    checksum = computeChecksum(userId=userId, appId=appId, scoreName="wrongScoreName")
    params = {"userId": userId, "appId": appId, "scoreName": "wrongScoreName"}
    response = client.get("/user/rank", params=params, headers={"checksum": checksum})
    assert response.status_code == 404
    assert response.json() == {'detail': 'Score name not found'}

def test_top_scores():
    k = 100
    checksum = computeChecksum(userId=userId, appId=appId, scoreName=scoreName, k=k)
    params = {"userId": userId, "appId": appId, "scoreName": scoreName, 'k': k}
    response = client.get("/leaderboard/top",
                          params=params,
                          headers={"checksum": checksum})
    assert response.status_code == 200
    assert response.json() == {
        'scores': [{'nickname': 'testNickname2', 'value': 120}],
        'userRank': 1,
        'userScore': 120
    }

def test_delete_score():
    checksum = computeChecksum(userId=userId, appId=appId, scoreName=scoreName)
    params = {"userId": userId, "appId": appId, "scoreName": scoreName}
    response = client.delete("/leaderboard",
                             params=params,
                             headers={"checksum": checksum})
    assert response.status_code == 200
    
    checksum = computeChecksum(userId=userId, appId=appId, scoreName="wrongScoreName")
    params = {"userId": userId, "appId": appId, "scoreName": "wrongScoreName"}
    response = client.delete("/leaderboard",
                             params=params,
                             headers={"checksum": checksum})
    assert response.status_code == 404
    assert response.json() == {'detail': 'Score name not found'}

def test_delete_user():
    def _deleteUser():
        checksum = computeChecksum(userId=userId)
        params = {"userId": userId}
        return client.delete("/user", params=params, headers={"checksum": checksum})
    response = _deleteUser()
    assert response.status_code == 200
    response = _deleteUser()
    assert response.status_code == 404
    assert response.json() == {"detail":"User not found"}
