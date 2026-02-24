"""Tests for /api/v1/clubs endpoints."""


def test_list_clubs_empty(client):
    res = client.get("/api/v1/clubs/")
    assert res.status_code == 200
    assert res.json() == []


def test_create_club(client):
    res = client.post("/api/v1/clubs/", json={"name": "Sunrise SC"})
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Sunrise SC"
    assert body["id"] >= 1
    assert "created_at" in body


def test_create_club_with_logo(client):
    res = client.post("/api/v1/clubs/", json={
        "name": "Logo FC",
        "logo_url": "https://example.com/logo.png",
    })
    assert res.status_code == 201
    assert res.json()["logo_url"] == "https://example.com/logo.png"


def test_get_club(client, club_id):
    res = client.get(f"/api/v1/clubs/{club_id}")
    assert res.status_code == 200
    assert res.json()["id"] == club_id
    assert res.json()["name"] == "Test FC"


def test_get_club_not_found(client):
    res = client.get("/api/v1/clubs/9999")
    assert res.status_code == 404


def test_list_clubs_after_create(client):
    client.post("/api/v1/clubs/", json={"name": "A"})
    client.post("/api/v1/clubs/", json={"name": "B"})
    res = client.get("/api/v1/clubs/")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_delete_club(client, club_id):
    res = client.delete(f"/api/v1/clubs/{club_id}")
    assert res.status_code == 204
    res = client.get(f"/api/v1/clubs/{club_id}")
    assert res.status_code == 404
