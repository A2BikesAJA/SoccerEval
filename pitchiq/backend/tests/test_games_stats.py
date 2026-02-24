"""Tests for /api/v1/games and /api/v1/stats endpoints."""


def test_list_games_empty(client):
    res = client.get("/api/v1/games/")
    assert res.status_code == 200
    assert res.json() == []


def test_get_game_not_found(client):
    res = client.get("/api/v1/games/9999")
    assert res.status_code == 404


def test_team_stats_empty(client):
    """Stats for a non-existent game returns empty list."""
    res = client.get("/api/v1/stats/game/9999/team")
    assert res.status_code == 200
    assert res.json() == []


def test_player_stats_empty(client):
    """Player stats for a non-existent game returns empty list."""
    res = client.get("/api/v1/stats/game/9999/players")
    assert res.status_code == 200
    assert res.json() == []


def test_player_history_empty(client):
    """Player history for non-existent player returns empty list."""
    res = client.get("/api/v1/stats/player/9999/history")
    assert res.status_code == 200
    assert res.json() == []
