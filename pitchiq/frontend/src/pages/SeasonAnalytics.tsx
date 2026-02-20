import { useState, useEffect } from 'react';
import { gamesApi } from '../lib/api';
import { cn } from '../lib/utils';

export default function SeasonAnalytics() {
  const [games, setGames] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    gamesApi.list()
      .then((res) => setGames(Array.isArray(res.data) ? res.data : []))
      .catch(() => setGames([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center py-16 text-slate-500">Loading season data...</div>;
  }

  const completed = games.filter((g) => g.status === 'completed');

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Season Analytics</h1>
        <p className="text-sm text-slate-400 mt-1">
          Season overview and performance trends
        </p>
      </div>

      {games.length === 0 ? (
        <div className="text-center py-16 bg-slate-800/50 rounded-xl border border-white/10">
          <h2 className="text-lg font-medium text-white mb-2">No Season Data Yet</h2>
          <p className="text-sm text-slate-400">
            Upload and process game footage to see season analytics and performance trends.
          </p>
        </div>
      ) : (
        <>
          {/* Season Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
            {[
              { label: 'Games', value: String(games.length) },
              { label: 'Completed', value: String(completed.length) },
              { label: 'Pending', value: String(games.length - completed.length) },
              { label: 'Status', value: completed.length === games.length ? 'All Processed' : 'Processing...' },
            ].map((stat) => (
              <div key={stat.label} className="bg-slate-800/50 rounded-xl border border-white/10 p-3">
                <div className="text-xs text-slate-400 mb-1">{stat.label}</div>
                <div className="text-lg font-bold text-white">{stat.value}</div>
              </div>
            ))}
          </div>

          {/* Games List */}
          <div className="bg-slate-800/50 rounded-xl border border-white/10 overflow-hidden">
            <div className="px-5 py-3 border-b border-white/10">
              <h3 className="text-sm font-medium text-white">All Games This Season</h3>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-2 px-4 text-slate-400 font-medium">Opponent</th>
                  <th className="text-center py-2 px-3 text-slate-400 font-medium">Date</th>
                  <th className="text-center py-2 px-3 text-slate-400 font-medium">Score</th>
                  <th className="text-center py-2 px-3 text-slate-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {games.map((g) => (
                  <tr key={g.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="py-2 px-4 font-medium text-white">vs {g.opponent_name}</td>
                    <td className="py-2 px-3 text-center text-slate-400">{g.game_date}</td>
                    <td className="py-2 px-3 text-center text-white font-bold">
                      {g.score_home != null ? `${g.score_home} - ${g.score_away}` : '—'}
                    </td>
                    <td className="py-2 px-3 text-center">
                      <span className={cn(
                        'text-xs px-2 py-0.5 rounded-full',
                        g.status === 'completed' ? 'bg-emerald-900/50 text-emerald-400' :
                        g.status === 'processing' ? 'bg-blue-900/50 text-blue-400' :
                        'bg-slate-700 text-slate-400',
                      )}>
                        {g.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
