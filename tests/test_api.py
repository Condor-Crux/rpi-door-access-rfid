import datetime
from app.core.time import utcnow

def test_create_account(client, db_session):
    payload = {
        "account_id": "ABC1",
        "status": "active",
        "expiration_date": (utcnow() + datetime.timedelta(days=5)).isoformat(),
        "credits": 10
    }
    response = client.post("/api/accounts", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ABC1"
    assert data["credits"] == 10

def test_recharge_account(client, db_session):
    payload = {
        "account_id": "ABC2",
        "status": "active",
        "expiration_date": (utcnow() + datetime.timedelta(days=5)).isoformat(),
        "credits": 10
    }
    client.post("/api/accounts", json=payload)
    
    response = client.put("/api/accounts/ABC2/recharge?amount=5")
    assert response.status_code == 200
    assert response.json()["new_credits"] == 15

def test_get_accounts(client, db_session):
    response = client.get("/api/accounts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
