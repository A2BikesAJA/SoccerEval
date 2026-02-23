"""Tests for health check and root endpoints."""


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "PitchIQ"
    assert "version" in body


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
