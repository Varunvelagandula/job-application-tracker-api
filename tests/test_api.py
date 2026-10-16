import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def auth(client, email="a@example.com"):
    r = client.post("/auth/register", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_register_duplicate_and_login(client):
    auth(client)
    dup = client.post("/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert dup.status_code == 409
    bad = client.post("/auth/login", json={"email": "a@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401
    ok = client.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert ok.status_code == 200


def test_requires_auth(client):
    assert client.get("/applications").status_code in (401, 403)


def test_crud_and_status_history(client):
    h = auth(client)
    r = client.post("/applications", json={"company": "Acme", "role": "SWE"}, headers=h)
    assert r.status_code == 201
    app_id = r.json()["id"]
    r = client.patch(f"/applications/{app_id}", json={"status": "interview"}, headers=h)
    assert [e["status"] for e in r.json()["events"]] == ["applied", "interview"]
    assert client.delete(f"/applications/{app_id}", headers=h).status_code == 204
    assert client.get(f"/applications/{app_id}", headers=h).status_code == 404


def test_users_cannot_see_each_others_data(client):
    h1, h2 = auth(client, "u1@example.com"), auth(client, "u2@example.com")
    app_id = client.post("/applications", json={"company": "X", "role": "Y"}, headers=h1).json()["id"]
    assert client.get(f"/applications/{app_id}", headers=h2).status_code == 404
    assert client.get("/applications", headers=h2).json() == []


def test_filter_search_and_validation(client):
    h = auth(client)
    client.post("/applications", json={"company": "Acme", "role": "Backend"}, headers=h)
    client.post("/applications", json={"company": "Globex", "role": "Data", "status": "offer"}, headers=h)
    assert len(client.get("/applications?status=offer", headers=h).json()) == 1
    assert len(client.get("/applications?q=acme", headers=h).json()) == 1
    bad = client.post("/applications", json={"company": "Z", "role": "R", "status": "nope"}, headers=h)
    assert bad.status_code == 422


def test_analytics(client):
    h = auth(client)
    client.post("/applications", json={"company": "A", "role": "R"}, headers=h)
    client.post("/applications", json={"company": "B", "role": "R", "status": "interview"}, headers=h)
    s = client.get("/analytics/summary", headers=h).json()
    assert s["total"] == 2 and s["response_rate"] == 0.5 and s["by_status"]["interview"] == 1
