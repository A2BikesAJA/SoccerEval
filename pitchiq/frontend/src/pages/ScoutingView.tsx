import { useState } from 'react';
import { cn } from '../lib/utils';
import PIQCard from '../components/PIQCard';
import PlayerComparison from '../components/PlayerComparison';

// Demo scouting data
const DEMO_SCOUTING_PLAYERS = [
  { id: 1, name: 'Marcus Johnson', position: 'CAM', ageGroup: 'U14', team: 'FC Warriors', tier: 'ECNL', tierNum: 1, ovr: 72, spd: 68, sht: 74, pas: 76, drb: 71, def: 42, phy: 63, games: 8, confidence: 'developing' as const },
  { id: 2, name: 'Ethan Williams', position: 'ST', ageGroup: 'U14', team: 'Storm SC', tier: 'MLS NEXT', tierNum: 1, ovr: 78, spd: 82, sht: 80, pas: 65, drb: 75, def: 35, phy: 72, games: 12, confidence: 'established' as const },
  { id: 3, name: 'Jayden Lopez', position: 'CM', ageGroup: 'U14', team: 'United FC', tier: 'ECRL', tierNum: 3, ovr: 68, spd: 64, sht: 55, pas: 78, drb: 70, def: 68, phy: 65, games: 6, confidence: 'developing' as const },
  { id: 4, name: 'Noah Chen', position: 'CB', ageGroup: 'U14', team: 'Galaxy Academy', tier: 'State Premier', tierNum: 5, ovr: 62, spd: 55, sht: 30, pas: 65, drb: 48, def: 78, phy: 72, games: 10, confidence: 'established' as const },
  { id: 5, name: 'Liam Anderson', position: 'LW', ageGroup: 'U14', team: 'Lightning FC', tier: 'ECNL', tierNum: 1, ovr: 70, spd: 80, sht: 68, pas: 62, drb: 78, def: 38, phy: 58, games: 7, confidence: 'developing' as const },
  { id: 6, name: 'Aiden Patel', position: 'GK', ageGroup: 'U14', team: 'FC Warriors', tier: 'ECNL', tierNum: 1, ovr: 66, spd: 48, sht: 25, pas: 62, drb: 40, def: 70, phy: 68, games: 8, confidence: 'developing' as const },
];

export default function ScoutingView() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterPosition, setFilterPosition] = useState('');
  const [filterAgeGroup, setFilterAgeGroup] = useState('');
  const [filterTier, setFilterTier] = useState<number | ''>('');
  const [sortBy, setSortBy] = useState('ovr');
  const [compareIds, setCompareIds] = useState<number[]>([]);
  const [showCompare, setShowCompare] = useState(false);

  const filtered = DEMO_SCOUTING_PLAYERS
    .filter((p) => {
      if (searchTerm && !p.name.toLowerCase().includes(searchTerm.toLowerCase())) return false;
      if (filterPosition && p.position !== filterPosition) return false;
      if (filterAgeGroup && p.ageGroup !== filterAgeGroup) return false;
      if (filterTier !== '' && p.tierNum !== filterTier) return false;
      return true;
    })
    .sort((a, b) => {
      const key = sortBy as keyof typeof a;
      return (b[key] as number) - (a[key] as number);
    });

  const toggleCompare = (id: number) => {
    if (compareIds.includes(id)) {
      setCompareIds(compareIds.filter((x) => x !== id));
    } else if (compareIds.length < 4) {
      setCompareIds([...compareIds, id]);
    }
  };

  const comparisonPlayers = compareIds.map((id) => {
    const p = DEMO_SCOUTING_PLAYERS.find((x) => x.id === id)!;
    return {
      playerName: p.name, clubName: p.team, position: p.position,
      ageGroup: p.ageGroup, competitionTier: p.tier,
      ovr: p.ovr, spd: p.spd, sht: p.sht, pas: p.pas, drb: p.drb, def: p.def, phy: p.phy,
      confidenceLevel: p.confidence, gamesAnalyzed: p.games,
    };
  });

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Scouting View</h1>
          <p className="text-sm text-slate-400 mt-1">Search, compare, and discover players across clubs</p>
        </div>
        {compareIds.length >= 2 && (
          <button
            onClick={() => setShowCompare(!showCompare)}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium text-white"
          >
            {showCompare ? 'Back to List' : `Compare ${compareIds.length} Players`}
          </button>
        )}
      </div>

      {showCompare ? (
        <PlayerComparison players={comparisonPlayers} />
      ) : (
        <>
          {/* Filters */}
          <div className="flex flex-wrap gap-3 mb-6">
            <input
              type="text"
              placeholder="Search players..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm placeholder-slate-500 w-48"
            />
            <select
              value={filterPosition}
              onChange={(e) => setFilterPosition(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="">All Positions</option>
              {['GK', 'CB', 'LB', 'RB', 'CDM', 'CM', 'CAM', 'LW', 'RW', 'ST'].map((p) => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>
            <select
              value={filterAgeGroup}
              onChange={(e) => setFilterAgeGroup(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="">All Age Groups</option>
              {['U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16', 'U17', 'U18', 'U19'].map((ag) => (
                <option key={ag} value={ag}>{ag}</option>
              ))}
            </select>
            <select
              value={filterTier}
              onChange={(e) => setFilterTier(e.target.value ? Number(e.target.value) : '')}
              className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="">All Tiers</option>
              {[1, 2, 3, 4, 5, 6, 7, 8].map((t) => (
                <option key={t} value={t}>Tier {t}</option>
              ))}
            </select>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
            >
              <option value="ovr">Sort: OVR</option>
              <option value="spd">Sort: Speed</option>
              <option value="sht">Sort: Shooting</option>
              <option value="pas">Sort: Passing</option>
              <option value="drb">Sort: Dribbling</option>
              <option value="def">Sort: Defending</option>
              <option value="phy">Sort: Physicality</option>
            </select>
          </div>

          {/* Player Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {filtered.map((player) => (
              <div key={player.id} className="relative">
                <div
                  className={cn(
                    'absolute top-2 right-2 z-10 w-6 h-6 rounded-full border-2 cursor-pointer flex items-center justify-center transition-all',
                    compareIds.includes(player.id)
                      ? 'border-emerald-400 bg-emerald-400 text-white'
                      : 'border-slate-500 hover:border-slate-400',
                  )}
                  onClick={() => toggleCompare(player.id)}
                >
                  {compareIds.includes(player.id) && (
                    <span className="text-xs font-bold">{compareIds.indexOf(player.id) + 1}</span>
                  )}
                </div>
                <PIQCard
                  playerName={player.name}
                  clubName={player.team}
                  position={player.position}
                  ageGroup={player.ageGroup}
                  competitionTier={player.tier}
                  ovr={player.ovr}
                  spd={player.spd}
                  sht={player.sht}
                  pas={player.pas}
                  drb={player.drb}
                  def={player.def}
                  phy={player.phy}
                  confidenceLevel={player.confidence}
                  gamesAnalyzed={player.games}
                  className="w-full"
                />
              </div>
            ))}
          </div>

          {filtered.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              No players match your filters.
            </div>
          )}
        </>
      )}
    </div>
  );
}
