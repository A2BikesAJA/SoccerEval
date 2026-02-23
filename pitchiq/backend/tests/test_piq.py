"""Tests for /api/v1/piq endpoints."""


def test_piq_player_not_found(client, team_id):
    """PIQ rating for a player with no rating data returns 404."""
    # Create a player first
    p = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "No Rating Player",
        "jersey_number": 99,
    })
    pid = p.json()["id"]
    res = client.get(f"/api/v1/piq/player/{pid}")
    assert res.status_code == 404


def test_piq_history_empty(client, team_id):
    """PIQ history for a player with no history returns empty list."""
    p = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "No History Player",
        "jersey_number": 88,
    })
    pid = p.json()["id"]
    res = client.get(f"/api/v1/piq/player/{pid}/history")
    assert res.status_code == 200
    assert res.json() == []


def test_scouting_empty(client):
    """Scouting endpoint with no data returns empty list."""
    res = client.get("/api/v1/piq/scouting")
    assert res.status_code == 200
    assert res.json() == []
