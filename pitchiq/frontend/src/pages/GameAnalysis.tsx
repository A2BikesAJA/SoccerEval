import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { gamesApi, statsApi } from '../lib/api';
import { cn } from '../lib/utils';
import StatsTable from '../components/StatsTable';
import TeamComparison from '../components/TeamComparison';
import HeatMap from '../components/HeatMap';
import ProcessingStatus from '../components/ProcessingStatus';

export default function GameAnalysis() {
  const { gameId } = useParams();
  const [selectedPlayer, setSelectedPlayer] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'players' | 'heatmap'>('overview');
  const [game, setGame] = useState<any>(null);
  const [teamStats, setTeamStats] = useState<any[]>([]);
  const [players, setPlayers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!gameId) return;
    const id = Number(gameId);
    Promise.all([
      gamesApi.get(id).then((r) => r.data).catch(() => null),
      statsApi.getTeamStats(id).then((r) => r.data).catch(() => []),
      statsApi.getPlayerStats(id).then((r) => r.data).catch(() => []),
    ])
      .then(([g, ts, ps]) => {
        setGame(g);
        setTeamStats(ts);
        setPlayers(ps);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [gameId]);

  if (loading) {
    return <div className="text-center py-16 text-slate-500">Loading game data...</div>;
  }

  if (!game) {
    return (
      <div className="text-center py-16">
        <h2 className="text-lg font-medium text-white mb-2">Game not found</h2>
        <Link to="/" className="text-emerald-400 hover:text-emerald-300 text-sm">Back to Dashboard</Link>
      </div>
    );
  }

  const gamePlayers = game.game_players || [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Game Analysis</h1>
          <p className="text-sm text-slate-400 mt-1">
            vs {game.opponent_name} — {game.game_date}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {game.score_home != null && (
            <span className="text-2xl font-black text-white">{game.score_home} - {game.score_away}</span>
          )}
          {game.score_home == null && (
            <span className="text-sm text-slate-400 capitalize">{game.status}</span>
          )}
        </div>
      </div>

      {/* Processing status for non-completed games */}
      {game.status !== 'completed' && (
        <div className="mb-6 p-6 bg-slate-800/50 rounded-xl border border-white/10 text-center">
          <p className="text-slate-400">
            This game is currently <span className="text-white font-medium">{game.status}</span>.
            Analytics will appear once processing is complete.
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-white/10">
        {(['overview', 'players', 'heatmap'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
              activeTab === tab
                ? 'text-white border-emerald-400'
                : 'text-slate-400 border-transparent hover:text-white',
            )}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {teamStats.length > 0 ? (
            <TeamComparison
              homeTeam="Home"
              awayTeam={game.opponent_name}
              stats={teamStats}
            />
          ) : (
            <div className="bg-slate-800/50 rounded-xl border border-white/10 p-8 text-center text-slate-500">
              No team stats available yet.
            </div>
          )}
          <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
            <h3 className="text-sm font-medium text-white mb-3">Game Info</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Date</span>
                <span className="text-white">{game.game_date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Status</span>
                <span className="text-white capitalize">{game.status}</span>
              </div>
              {game.formation && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Formation</span>
                  <span className="text-white">{game.formation}</span>
                </div>
              )}
              {game.age_group && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Age Group</span>
                  <span className="text-white">{game.age_group}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-400">Players</span>
                <span className="text-white">{gamePlayers.length}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Players Tab */}
      {activeTab === 'players' && (
        <div>
          {players.length > 0 ? (
            <>
              <div className="mb-3 flex items-center gap-3 text-xs text-slate-500">
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
                  &gt;70% screen time
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 inline-block" />
                  40-70% screen time
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
                  &lt;40% screen time
                </span>
                <span className="ml-2">~extrapolated</span>
              </div>
              <StatsTable
                players={players}
                onPlayerClick={(id) => setSelectedPlayer(id)}
              />
            </>
          ) : (
            <div className="text-center py-12 text-slate-500">
              No player stats available yet. Stats appear after processing completes.
            </div>
          )}
        </div>
      )}

      {/* Heatmap Tab */}
      {activeTab === 'heatmap' && (
        <div className="text-center py-12 text-slate-500">
          Heatmap data will appear after game processing completes.
        </div>
      )}
    </div>
  );
}
