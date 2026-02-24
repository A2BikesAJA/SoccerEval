"""Shared test fixtures — in-memory SQLite database + FastAPI test client."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base, get_db
from app.main import app

# In-memory SQLite for isolation
TEST_DATABASE_URL = "sqlite:///file::memory:?cache=shared"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def club_id(client):
    """Create a club and return its id."""
    res = client.post("/api/v1/clubs/", json={"name": "Test FC"})
    assert res.status_code == 201
    return res.json()["id"]


@pytest.fixture()
def team_id(client, club_id):
    """Create a team and return its id."""
    res = client.post("/api/v1/teams/", json={
        "club_id": club_id,
        "name": "Test FC U12",
        "age_group": "U12",
        "competition_tier": 6,
    })
    assert res.status_code == 201
    return res.json()["id"]
