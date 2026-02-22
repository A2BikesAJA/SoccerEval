import { useState, useEffect } from 'react';
import { clubsApi, teamsApi, playersApi } from '../lib/api';
import CompetitionTierSelector from '../components/CompetitionTierSelector';

interface PlayerEntry {
  id: number | null;
  jersey_number: number;
  name: string;
  position: string;
}

const POSITIONS = ['GK', 'CB', 'LB', 'RB', 'CDM', 'CM', 'CAM', 'LW', 'RW', 'ST'];

const FORMATIONS = [
  '4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '3-4-3',
  '4-1-4-1', '4-3-1-2', '5-3-2', '4-5-1', '3-3-4',
];

export default function Settings() {
  // Existing entity IDs (null = not yet created)
  const [clubId, setClubId] = useState<number | null>(null);
  const [teamId, setTeamId] = useState<number | null>(null);

  // Club / Team fields
  const [clubName, setClubName] = useState('');
  const [teamName, setTeamName] = useState('');
  const [tier, setTier] = useState(6);
  const [ageGroup, setAgeGroup] = useState('U12');
  const [leagueName, setLeagueName] = useState('');
  const [defaultCamera, setDefaultCamera] = useState('veo_followcam');
  const [piqMinGames, setPiqMinGames] = useState(3);
  const [detectionFps, setDetectionFps] = useState(2.0);
  const [defaultFormation, setDefaultFormation] = useState('');

  // Save state
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Players
  const [players, setPlayers] = useState<PlayerEntry[]>([]);
  const [playerSaving, setPlayerSaving] = useState(false);
  const [playerSaved, setPlayerSaved] = useState(false);
  const [playerError, setPlayerError] = useState<string | null>(null);

  // Load existing club + team + players on mount
  useEffect(() => {
    const load = async () => {
      try {
        const clubsRes = await clubsApi.list();
        const clubs = clubsRes.data;
        if (clubs.length > 0) {
          const club = clubs[0];
          setClubId(club.id);
          setClubName(club.name);

          const teamsRes = await teamsApi.list(club.id);
          const teams = teamsRes.data;
          if (teams.length > 0) {
            const team = teams[0];
            setTeamId(team.id);
            // Strip the club name prefix if present
            const displayTeamName = team.name.startsWith(`${club.name} `)
              ? team.name.slice(club.name.length + 1)
              : team.name;
            setTeamName(displayTeamName);
            setAgeGroup(team.age_group || 'U12');
            setTier(team.competition_tier ?? 6);
            setLeagueName(team.league_name || '');
            setDefaultFormation(team.default_formation || '');

            // Load players for this team
            const playersRes = await playersApi.list(team.id);
            setPlayers(
              playersRes.data.map((p: any) => ({
                id: p.id,
                jersey_number: p.jersey_number ?? 0,
                name: p.name,
                position: p.position || '',
              }))
            );
          }
        }
      } catch {
        // Backend not running or no data yet
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const handleSave = async () => {
    setSaveError(null);
    if (!clubName.trim() || !teamName.trim()) {
      setSaveError('Club name and team name are required.');
      return;
    }
    try {
      let currentClubId = clubId;
      let currentTeamId = teamId;

      if (!currentClubId) {
        const clubRes = await clubsApi.create({ name: clubName });
        currentClubId = clubRes.data.id;
        setClubId(currentClubId);
      }

      if (!currentTeamId) {
        const teamRes = await teamsApi.create({
          club_id: currentClubId,
          name: `${clubName} ${teamName}`,
          age_group: ageGroup,
          competition_tier: tier,
          league_name: leagueName || null,
          default_formation: defaultFormation || null,
        });
        currentTeamId = teamRes.data.id;
        setTeamId(currentTeamId);
      } else {
        await teamsApi.update(currentTeamId, {
          club_id: currentClubId,
          name: `${clubName} ${teamName}`,
          age_group: ageGroup,
          competition_tier: tier,
          league_name: leagueName || null,
          default_formation: defaultFormation || null,
        });
      }

      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setSaveError(detail || err.message || 'Save failed. Make sure the backend is running.');
    }
  };

  // Player management
  const addPlayer = () => {
    const nextNum = players.length > 0 ? Math.max(...players.map((p) => p.jersey_number)) + 1 : 1;
    setPlayers([...players, { id: null, jersey_number: nextNum, name: '', position: '' }]);
  };

  const updatePlayer = (idx: number, field: keyof PlayerEntry, value: string | number) => {
    const updated = [...players];
    (updated[idx] as any)[field] = value;
    setPlayers(updated);
  };

  const removePlayer = async (idx: number) => {
    const player = players[idx];
    if (player.id) {
      try {
        await playersApi.delete(player.id);
      } catch {
        // Player may already be deleted
      }
    }
    setPlayers(players.filter((_, i) => i !== idx));
  };

  const saveRoster = async () => {
    if (!teamId) {
      setPlayerError('Save your club & team first before adding players.');
      return;
    }
    setPlayerSaving(true);
    setPlayerError(null);
    try {
      const roster = players
        .filter((p) => p.name.trim())
        .map((p) => ({
          jersey_number: p.jersey_number,
          name: p.name,
          position: p.position || null,
        }));
      const res = await playersApi.importRoster(teamId, roster);
      setPlayers(
        res.data.map((p: any) => ({
          id: p.id,
          jersey_number: p.jersey_number ?? 0,
          name: p.name,
          position: p.position || '',
        }))
      );
      setPlayerSaved(true);
      setTimeout(() => setPlayerSaved(false), 3000);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setPlayerError(detail || err.message || 'Failed to save roster.');
    } finally {
      setPlayerSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-2xl">
        <div className="text-center py-12 text-slate-500">Loading settings...</div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Manage your club, team, roster, and processing preferences</p>
      </div>

      <div className="space-y-8">
        {/* Club Profile */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Club Profile</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Club Name</label>
              <input
                type="text"
                value={clubName}
                onChange={(e) => setClubName(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Team Name</label>
              <input
                type="text"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Age Group</label>
                <select
                  value={ageGroup}
                  onChange={(e) => setAgeGroup(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
                >
                  {['U8','U9','U10','U11','U12','U13','U14','U15','U16','U17','U18','U19'].map((ag) => (
                    <option key={ag} value={ag}>{ag}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">League Name</label>
                <input
                  type="text"
                  value={leagueName}
                  onChange={(e) => setLeagueName(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Competition Tier */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Competition Tier</h2>
          <CompetitionTierSelector value={tier} onChange={setTier} />
        </section>

        {/* Default Formation */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Default Formation</h2>
          <div className="grid grid-cols-5 gap-2">
            {FORMATIONS.map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setDefaultFormation(f === defaultFormation ? '' : f)}
                className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                  defaultFormation === f
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-3">
            This will be pre-selected when uploading new games. You can still change it per game.
          </p>
        </section>

        {/* Save Club & Team */}
        {saveError && (
          <div className="p-3 bg-red-900/20 border border-red-800/30 rounded-lg">
            <p className="text-sm text-red-400">{saveError}</p>
          </div>
        )}
        <button
          onClick={handleSave}
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-semibold text-white transition-colors"
        >
          {saved ? (clubId ? 'Settings Saved!' : 'Club & Team Created!') : (clubId ? 'Save Settings' : 'Save & Create Team')}
        </button>

        {/* Player Roster */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white">Player Roster</h2>
              <p className="text-xs text-slate-400 mt-0.5">
                {teamId
                  ? `${players.length} player${players.length !== 1 ? 's' : ''} on roster`
                  : 'Save your club & team above first'}
              </p>
            </div>
            <button
              type="button"
              onClick={addPlayer}
              disabled={!teamId}
              className="text-xs px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-lg text-white transition-colors"
            >
              + Add Player
            </button>
          </div>

          {players.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-slate-500 text-sm mb-1">No players on the roster yet.</p>
              <p className="text-slate-600 text-xs">Click "+ Add Player" above to start building your roster.</p>
            </div>
          ) : (
            <div className="space-y-1.5 max-h-80 overflow-y-auto pr-1">
              <div className="flex gap-2 items-center px-3 py-1 text-xs text-slate-500">
                <span className="w-14 text-center">#</span>
                <span className="flex-1">Name</span>
                <span className="w-20 text-center">Position</span>
                <span className="w-6" />
              </div>
              {players.map((entry, idx) => (
                <div
                  key={entry.id ?? `new-${idx}`}
                  className="flex gap-2 items-center px-3 py-2 rounded-lg border bg-slate-800/60 border-slate-600"
                >
                  <input
                    type="number"
                    value={entry.jersey_number}
                    onChange={(e) => updatePlayer(idx, 'jersey_number', parseInt(e.target.value) || 0)}
                    className="w-14 bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-white text-center text-sm"
                    placeholder="#"
                    min={0}
                  />
                  <input
                    type="text"
                    value={entry.name}
                    onChange={(e) => updatePlayer(idx, 'name', e.target.value)}
                    className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-3 py-1 text-white text-sm placeholder-slate-500"
                    placeholder="Player name"
                  />
                  <select
                    value={entry.position}
                    onChange={(e) => updatePlayer(idx, 'position', e.target.value)}
                    className="w-20 bg-slate-700 border border-slate-600 rounded-lg px-2 py-1 text-white text-sm"
                  >
                    <option value="">Pos</option>
                    {POSITIONS.map((pos) => (
                      <option key={pos} value={pos}>{pos}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => removePlayer(idx)}
                    className="text-slate-500 hover:text-red-400 text-sm px-1"
                  >
                    x
                  </button>
                </div>
              ))}
            </div>
          )}

          {playerError && (
            <div className="mt-3 p-3 bg-red-900/20 border border-red-800/30 rounded-lg">
              <p className="text-sm text-red-400">{playerError}</p>
            </div>
          )}

          {players.length > 0 && (
            <button
              type="button"
              onClick={saveRoster}
              disabled={playerSaving || !teamId}
              className="mt-4 w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 rounded-xl font-semibold text-white text-sm transition-colors"
            >
              {playerSaving ? 'Saving...' : playerSaved ? 'Roster Saved!' : 'Save Roster'}
            </button>
          )}
        </section>

        {/* PIQ Rating Preferences */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">PIQ Rating Preferences</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Minimum games for PIQ Rating display
              </label>
              <select
                value={piqMinGames}
                onChange={(e) => setPiqMinGames(Number(e.target.value))}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              >
                {[2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>{n} games</option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                Players with fewer games will show "Calculating..." instead of a rating.
              </p>
            </div>
          </div>
        </section>

        {/* Processing Preferences */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Processing Preferences</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Default Camera Platform</label>
              <select
                value={defaultCamera}
                onChange={(e) => setDefaultCamera(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="veo_followcam">VEO Follow Cam</option>
                <option value="veo_panoramic">VEO Panoramic</option>
                <option value="trace">Trace</option>
                <option value="pixellot">Pixellot</option>
                <option value="sideline">Sideline Camera</option>
                <option value="static_elevated">Static Elevated</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Detection Frame Rate (fps)
              </label>
              <select
                value={detectionFps}
                onChange={(e) => setDetectionFps(Number(e.target.value))}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value={0.5}>0.5 fps (faster processing, lower accuracy)</option>
                <option value={1.0}>1.0 fps (balanced)</option>
                <option value={2.0}>2.0 fps (recommended)</option>
                <option value={4.0}>4.0 fps (higher accuracy, slower)</option>
              </select>
            </div>
          </div>
        </section>

        {/* Export */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Data Export</h2>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors">
              Export All Stats (CSV)
            </button>
            <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors">
              Export PIQ Ratings (CSV)
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
