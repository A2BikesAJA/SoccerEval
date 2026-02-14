import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '../lib/utils';

interface GameSummary {
  id: number;
  opponent_name: string;
  game_date: string;
  status: string;
  score_home?: number;
  score_away?: number;
}


function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn(
      'text-xs px-2 py-0.5 rounded-full font-medium',
      status === 'completed' ? 'bg-emerald-900/50 text-emerald-400' :
      status === 'processing' ? 'bg-blue-900/50 text-blue-400' :
      status === 'error' ? 'bg-red-900/50 text-red-400' :
      'bg-slate-700 text-slate-400',
    )}>
      {status}
    </span>
  );
}

export default function Dashboard() {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/v1/games/')
      .then((res) => res.ok ? res.json() : [])
      .then((data) => setGames(data))
      .catch(() => setGames([]))
      .finally(() => setLoading(false));
  }, []);

  const completed = games.filter((g) => g.status === 'completed');

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">Overview of your team's analytics</p>
        </div>
        <Link
          to="/upload"
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium text-white transition-colors"
        >
          Upload Game
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Games Analyzed', value: String(completed.length), icon: '◎' },
          { label: 'Total Games', value: String(games.length), icon: '⊕' },
          { label: 'Completed', value: String(completed.length), icon: '★' },
          { label: 'Pending', value: String(games.length - completed.length), icon: '⊞' },
        ].map((stat) => (
          <div key={stat.label} className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 uppercase tracking-wider">{stat.label}</span>
              <span className="text-slate-600">{stat.icon}</span>
            </div>
            <div className="text-2xl font-bold text-white mt-2">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Recent Games */}
      {games.length > 0 && (
        <div className="bg-slate-800/50 rounded-xl border border-white/10 overflow-hidden">
          <div className="px-5 py-3 border-b border-white/10">
            <h2 className="text-sm font-medium text-white">Recent Games</h2>
          </div>
          <div className="divide-y divide-white/5">
            {games.map((game) => (
              <Link
                key={game.id}
                to={`/game/${game.id}`}
                className="flex items-center justify-between px-5 py-3 hover:bg-white/5 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <div className="text-sm font-medium text-white">vs {game.opponent_name}</div>
                  <StatusBadge status={game.status} />
                </div>
                <div className="flex items-center gap-4">
                  {game.score_home != null && (
                    <span className="text-sm font-bold text-white">
                      {game.score_home} - {game.score_away}
                    </span>
                  )}
                  <span className="text-xs text-slate-500">{game.game_date}</span>
                  <span className="text-slate-500">→</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && games.length === 0 && (
        <div className="text-center py-16">
          <div className="text-4xl mb-4">⊞</div>
          <h2 className="text-lg font-medium text-white mb-2">No games yet</h2>
          <p className="text-sm text-slate-400 mb-4">
            Upload your first game video to start tracking player analytics.
          </p>
          <Link
            to="/upload"
            className="inline-block px-4 py-2 bg-emerald-600 hover:bg-emerald-500 rounded-lg text-sm font-medium text-white transition-colors"
          >
            Upload Game
          </Link>
        </div>
      )}
    </div>
  );
}
