"""Tests for /api/v1/teams endpoints — covers Settings page team save flow."""


def test_list_teams_empty(client):
    res = client.get("/api/v1/teams/")
    assert res.status_code == 200
    assert res.json() == []


def test_create_team(client, club_id):
    res = client.post("/api/v1/teams/", json={
        "club_id": club_id,
        "name": "Test FC U14",
        "age_group": "U14",
        "competition_tier": 4,
        "league_name": "NPL",
        "default_formation": "4-3-3",
        "default_match_format": "11v11",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "Test FC U14"
    assert body["age_group"] == "U14"
    assert body["competition_tier"] == 4
    assert body["league_name"] == "NPL"
    assert body["default_formation"] == "4-3-3"
    assert body["default_match_format"] == "11v11"
    assert body["id"] >= 1


def test_create_team_all_age_groups(client, club_id):
    """Verify every AgeGroup enum value is accepted."""
    for ag in ["U8", "U9", "U10", "U11", "U12", "U13",
               "U14", "U15", "U16", "U17", "U18", "U19"]:
        res = client.post("/api/v1/teams/", json={
            "club_id": club_id,
            "name": f"Team {ag}",
            "age_group": ag,
        })
        assert res.status_code == 201, f"Failed for age_group={ag}: {res.text}"
        assert res.json()["age_group"] == ag


def test_create_team_all_tiers(client, club_id):
    """Verify competition_tier 1–8 are accepted."""
    for tier in range(1, 9):
        res = client.post("/api/v1/teams/", json={
            "club_id": club_id,
            "name": f"Tier {tier} Team",
            "age_group": "U12",
            "competition_tier": tier,
        })
        assert res.status_code == 201, f"Failed for tier={tier}: {res.text}"
        assert res.json()["competition_tier"] == tier


def test_create_team_all_match_formats(client, club_id):
    """Verify all match formats (5v5, 7v7, 9v9, 11v11) are accepted."""
    formats = ["5v5", "7v7", "9v9", "11v11"]
    for fmt in formats:
        res = client.post("/api/v1/teams/", json={
            "club_id": club_id,
            "name": f"Team {fmt}",
            "age_group": "U12",
            "default_match_format": fmt,
        })
        assert res.status_code == 201, f"Failed for match_format={fmt}: {res.text}"
        assert res.json()["default_match_format"] == fmt


def test_create_team_all_formations_by_format(client, club_id):
    """Verify formations for every match format are accepted."""
    formations_by_format = {
        "5v5": ["1-2-1", "2-2", "2-1-1", "1-1-2", "3-1", "1-3"],
        "7v7": ["2-3-1", "3-2-1", "3-1-2", "2-1-2-1", "1-2-1-2", "3-3"],
        "9v9": ["3-3-2", "3-2-3", "2-4-2", "3-2-1-2", "2-3-3", "3-1-3-1"],
        "11v11": [
            "4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "3-4-3",
            "4-1-4-1", "4-3-1-2", "5-3-2", "4-5-1", "3-3-4",
        ],
    }
    for fmt, formations in formations_by_format.items():
        for f in formations:
            res = client.post("/api/v1/teams/", json={
                "club_id": club_id,
                "name": f"Team {fmt} {f}",
                "age_group": "U12",
                "default_match_format": fmt,
                "default_formation": f,
            })
            assert res.status_code == 201, f"Failed for {fmt}/{f}: {res.text}"
            assert res.json()["default_formation"] == f
            assert res.json()["default_match_format"] == fmt


def test_list_teams_by_club(client, club_id):
    client.post("/api/v1/teams/", json={
        "club_id": club_id,
        "name": "Team A",
        "age_group": "U12",
    })
    res = client.get("/api/v1/teams/", params={"club_id": club_id})
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["club_id"] == club_id


def test_get_team(client, team_id):
    res = client.get(f"/api/v1/teams/{team_id}")
    assert res.status_code == 200
    assert res.json()["id"] == team_id


def test_get_team_not_found(client):
    res = client.get("/api/v1/teams/9999")
    assert res.status_code == 404


def test_update_team(client, club_id, team_id):
    """Simulate the Settings page 'Save Settings' button for an existing team."""
    res = client.put(f"/api/v1/teams/{team_id}", json={
        "club_id": club_id,
        "name": "Updated FC U13",
        "age_group": "U13",
        "competition_tier": 5,
        "league_name": "State Premier",
        "default_formation": "4-4-2",
        "default_match_format": "11v11",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["name"] == "Updated FC U13"
    assert body["age_group"] == "U13"
    assert body["competition_tier"] == 5
    assert body["league_name"] == "State Premier"
    assert body["default_formation"] == "4-4-2"
    assert body["default_match_format"] == "11v11"


def test_update_team_match_format_change(client, club_id, team_id):
    """Change match format from 11v11 to 7v7 and update formation."""
    res = client.put(f"/api/v1/teams/{team_id}", json={
        "club_id": club_id,
        "name": "Test FC U10",
        "age_group": "U10",
        "default_match_format": "7v7",
        "default_formation": "2-3-1",
    })
    assert res.status_code == 200
    assert res.json()["default_match_format"] == "7v7"
    assert res.json()["default_formation"] == "2-3-1"


def test_update_team_formation_toggle(client, club_id, team_id):
    """Set a formation, then clear it (like toggling off in the UI)."""
    # Set formation
    res = client.put(f"/api/v1/teams/{team_id}", json={
        "club_id": club_id,
        "name": "Test FC U12",
        "age_group": "U12",
        "default_formation": "3-5-2",
    })
    assert res.status_code == 200
    assert res.json()["default_formation"] == "3-5-2"

    # Clear formation
    res = client.put(f"/api/v1/teams/{team_id}", json={
        "club_id": club_id,
        "name": "Test FC U12",
        "age_group": "U12",
        "default_formation": None,
    })
    assert res.status_code == 200
    assert res.json()["default_formation"] is None


def test_delete_team(client, team_id):
    res = client.delete(f"/api/v1/teams/{team_id}")
    assert res.status_code == 204
    res = client.get(f"/api/v1/teams/{team_id}")
    assert res.status_code == 404
