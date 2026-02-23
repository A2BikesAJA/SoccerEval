"""Tests for /api/v1/players endpoints — covers Settings page roster flow."""


def test_list_players_empty(client):
    res = client.get("/api/v1/players/")
    assert res.status_code == 200
    assert res.json() == []


def test_create_player(client, team_id):
    res = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "John Doe",
        "jersey_number": 10,
        "position": "ST",
    })
    assert res.status_code == 201
    body = res.json()
    assert body["name"] == "John Doe"
    assert body["jersey_number"] == 10
    assert body["position"] == "ST"


def test_create_player_all_positions(client, team_id):
    """Verify all positions from the Settings UI are accepted."""
    positions = ["GK", "CB", "LB", "RB", "CDM", "CM", "CAM", "LW", "RW", "ST"]
    for i, pos in enumerate(positions):
        res = client.post("/api/v1/players/", json={
            "team_id": team_id,
            "name": f"Player {pos}",
            "jersey_number": i + 1,
            "position": pos,
        })
        assert res.status_code == 201, f"Failed for position={pos}: {res.text}"
        assert res.json()["position"] == pos


def test_create_player_no_position(client, team_id):
    """Position is optional in the UI."""
    res = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "No Pos Player",
        "jersey_number": 99,
    })
    assert res.status_code == 201
    assert res.json()["position"] is None


def test_list_players_by_team(client, team_id):
    client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "Player One",
        "jersey_number": 1,
    })
    res = client.get("/api/v1/players/", params={"team_id": team_id})
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_get_player(client, team_id):
    create = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "Get Me",
        "jersey_number": 7,
    })
    pid = create.json()["id"]
    res = client.get(f"/api/v1/players/{pid}")
    assert res.status_code == 200
    assert res.json()["name"] == "Get Me"


def test_get_player_not_found(client):
    res = client.get("/api/v1/players/9999")
    assert res.status_code == 404


def test_update_player(client, team_id):
    create = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "Old Name",
        "jersey_number": 5,
        "position": "CB",
    })
    pid = create.json()["id"]
    res = client.put(f"/api/v1/players/{pid}", json={
        "team_id": team_id,
        "name": "New Name",
        "jersey_number": 5,
        "position": "CDM",
    })
    assert res.status_code == 200
    assert res.json()["name"] == "New Name"
    assert res.json()["position"] == "CDM"


def test_delete_player(client, team_id):
    create = client.post("/api/v1/players/", json={
        "team_id": team_id,
        "name": "Delete Me",
        "jersey_number": 88,
    })
    pid = create.json()["id"]
    res = client.delete(f"/api/v1/players/{pid}")
    assert res.status_code == 204
    res = client.get(f"/api/v1/players/{pid}")
    assert res.status_code == 404


def test_import_roster(client, team_id):
    """Simulate the Settings page 'Save Roster' button."""
    roster = [
        {"jersey_number": 1, "name": "Keeper Kate", "position": "GK"},
        {"jersey_number": 4, "name": "Defender Dave", "position": "CB"},
        {"jersey_number": 7, "name": "Midfielder Mike", "position": "CM"},
        {"jersey_number": 9, "name": "Striker Sam", "position": "ST"},
        {"jersey_number": 11, "name": "Winger Will", "position": "LW"},
    ]
    res = client.post(f"/api/v1/players/roster/{team_id}", json=roster)
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 5
    names = {p["name"] for p in body}
    assert "Keeper Kate" in names
    assert "Striker Sam" in names
    # All players should have IDs
    assert all(p["id"] is not None for p in body)


def test_import_roster_upsert(client, team_id):
    """Roster import should update existing players by jersey number."""
    # First import
    roster1 = [
        {"jersey_number": 10, "name": "Original Name", "position": "CAM"},
    ]
    client.post(f"/api/v1/players/roster/{team_id}", json=roster1)

    # Second import — same jersey, different name
    roster2 = [
        {"jersey_number": 10, "name": "Updated Name", "position": "CAM"},
    ]
    res = client.post(f"/api/v1/players/roster/{team_id}", json=roster2)
    assert res.status_code == 200
    assert res.json()[0]["name"] == "Updated Name"

    # Should not have duplicates
    all_players = client.get("/api/v1/players/", params={"team_id": team_id}).json()
    jersey_10 = [p for p in all_players if p["jersey_number"] == 10]
    assert len(jersey_10) == 1


def test_import_roster_null_position(client, team_id):
    """Roster entries with null position (user left position blank)."""
    roster = [
        {"jersey_number": 3, "name": "No Position Player", "position": None},
    ]
    res = client.post(f"/api/v1/players/roster/{team_id}", json=roster)
    assert res.status_code == 200
    assert res.json()[0]["position"] is None


def test_full_settings_flow(client):
    """End-to-end: create club → create team with formation → save roster."""
    # Step 1: Create club
    club_res = client.post("/api/v1/clubs/", json={"name": "Sunrise SC"})
    assert club_res.status_code == 201
    club_id = club_res.json()["id"]

    # Step 2: Create team with formation
    team_res = client.post("/api/v1/teams/", json={
        "club_id": club_id,
        "name": "Sunrise SC U12 Boys",
        "age_group": "U12",
        "competition_tier": 6,
        "league_name": "Florida Premier League",
        "default_formation": "4-3-3",
    })
    assert team_res.status_code == 201
    team_id = team_res.json()["id"]
    assert team_res.json()["default_formation"] == "4-3-3"

    # Step 3: Verify team loads correctly (Settings page load)
    clubs = client.get("/api/v1/clubs/").json()
    assert len(clubs) == 1
    teams = client.get("/api/v1/teams/", params={"club_id": club_id}).json()
    assert len(teams) == 1
    assert teams[0]["default_formation"] == "4-3-3"

    # Step 4: Save roster
    roster = [
        {"jersey_number": 1, "name": "Alex Keeper", "position": "GK"},
        {"jersey_number": 4, "name": "Ben Back", "position": "CB"},
        {"jersey_number": 8, "name": "Chris Mid", "position": "CM"},
        {"jersey_number": 9, "name": "Dan Striker", "position": "ST"},
    ]
    roster_res = client.post(f"/api/v1/players/roster/{team_id}", json=roster)
    assert roster_res.status_code == 200
    assert len(roster_res.json()) == 4

    # Step 5: Verify players load correctly
    players = client.get("/api/v1/players/", params={"team_id": team_id}).json()
    assert len(players) == 4

    # Step 6: Update settings (change formation)
    update_res = client.put(f"/api/v1/teams/{team_id}", json={
        "club_id": club_id,
        "name": "Sunrise SC U12 Boys",
        "age_group": "U12",
        "competition_tier": 5,
        "league_name": "State Premier",
        "default_formation": "4-4-2",
    })
    assert update_res.status_code == 200
    assert update_res.json()["default_formation"] == "4-4-2"
    assert update_res.json()["competition_tier"] == 5
