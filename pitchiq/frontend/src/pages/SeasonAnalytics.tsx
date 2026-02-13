import { useState } from 'react';
import { cn } from '../lib/utils';
import DevelopmentTimeline from '../components/DevelopmentTimeline';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

// Demo season data
const DEMO_TEAM_PERFORMANCE = [
  { game: 'vs Lightning', date: 'Sep 7', result: 'W', score: '2-0', teamScore: 6.8 },
  { game: 'vs Storm', date: 'Sep 21', result: 'L', score: '1-3', teamScore: 5.2 },
  { game: 'vs Galaxy', date: 'Oct 5', result: 'W', score: '4-1', teamScore: 7.5 },
  { game: 'vs United', date: 'Oct 19', result: 'D', score: '2-2', teamScore: 6.4 },
  { game: 'vs Cosmos', date: 'Nov 1', result: 'W', score: '1-0', teamScore: 6.9 },
  { game: 'vs Storm', date: 'Nov 8', result: 'D', score: '2-2', teamScore: 6.5 },
  { game: 'vs Lightning', date: 'Nov 15', result: 'W', score: '3-1', teamScore: 7.8 },
];

const DEMO_PLAYER_SEASON = [
  { name: 'Marcus Johnson', position: 'CAM', games: 7, avgScore: 7.6, goals: 8, assists: 5, piqOvr: 72, piqChange: '+7' },
  { name: 'Alex Rivera', position: 'ST', games: 7, avgScore: 7.2, goals: 10, assists: 2, piqOvr: 70, piqChange: '+5' },
  { name: 'David Kim', position: 'CDM', games: 6, avgScore: 7.0, goals: 1, assists: 3, piqOvr: 68, piqChange: '+4' },
  { name: 'Liam Anderson', position: 'LW', games: 7, avgScore: 6.8, goals: 4, assists: 6, piqOvr: 70, piqChange: '+8' },
  { name: 'Chris Taylor', position: 'CB', games: 7, avgScore: 6.5, goals: 0, assists: 0, piqOvr: 64, piqChange: '+3' },
  { name: 'Aiden Patel', position: 'GK', games: 7, avgScore: 6.9, goals: 0, assists: 0, piqOvr: 66, piqChange: '+5' },
];

export default function SeasonAnalytics() {
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Season Analytics</h1>
        <p className="text-sm text-slate-400 mt-1">
          FC Warriors U14 — Fall 2025 Season
        </p>
      </div>

      {/* Season Summary */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-8">
        {[
          { label: 'Record', value: '4W 2D 1L' },
          { label: 'Goals For', value: '15' },
          { label: 'Goals Against', value: '9' },
          { label: 'Avg Score', value: '6.7' },
          { label: 'Top Scorer', value: 'Rivera (10)' },
          { label: 'Top Assist', value: 'Anderson (6)' },
        ].map((stat) => (
          <div key={stat.label} className="bg-slate-800/50 rounded-xl border border-white/10 p-3">
            <div className="text-xs text-slate-400 mb-1">{stat.label}</div>
            <div className="text-lg font-bold text-white">{stat.value}</div>
          </div>
        ))}
      </div>

      {/* Team Performance Chart */}
      <div className="bg-slate-800/50 rounded-xl border border-white/10 p-5 mb-6">
        <h3 className="text-sm font-medium text-white mb-3">Team Performance Over Season</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={DEMO_TEAM_PERFORMANCE}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <YAxis domain={[0, 10]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1e293b',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8, fontSize: 12,
              }}
            />
            <Bar
              dataKey="teamScore"
              fill="#22c55e"
              radius={[4, 4, 0, 0]}
              name="Team Score"
            />
          </BarChart>
        </ResponsiveContainer>

        {/* Game results legend */}
        <div className="flex gap-4 mt-2">
          {DEMO_TEAM_PERFORMANCE.map((g) => (
            <div key={g.date} className="flex items-center gap-1 text-xs">
              <span className={cn(
                'w-4 h-4 rounded-sm flex items-center justify-center font-bold',
                g.result === 'W' ? 'bg-emerald-900/50 text-emerald-400' :
                g.result === 'D' ? 'bg-yellow-900/50 text-yellow-400' :
                'bg-red-900/50 text-red-400',
              )}>
                {g.result}
              </span>
              <span className="text-slate-500">{g.score}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Player Season Stats Table */}
      <div className="bg-slate-800/50 rounded-xl border border-white/10 overflow-hidden mb-6">
        <div className="px-5 py-3 border-b border-white/10">
          <h3 className="text-sm font-medium text-white">Player Season Summary</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left py-2 px-4 text-slate-400 font-medium">Player</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">POS</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">GP</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">Avg Score</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">G</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">A</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">PIQ OVR</th>
              <th className="text-center py-2 px-3 text-slate-400 font-medium">Change</th>
            </tr>
          </thead>
          <tbody>
            {DEMO_PLAYER_SEASON.map((p) => (
              <tr key={p.name} className="border-b border-white/5 hover:bg-white/5 cursor-pointer">
                <td className="py-2 px-4 font-medium text-white">{p.name}</td>
                <td className="py-2 px-3 text-center text-slate-400">{p.position}</td>
                <td className="py-2 px-3 text-center text-slate-400">{p.games}</td>
                <td className="py-2 px-3 text-center">
                  <span className={cn(
                    'font-bold',
                    p.avgScore >= 7 ? 'text-emerald-400' : p.avgScore >= 6 ? 'text-blue-400' : 'text-slate-400',
                  )}>
                    {p.avgScore.toFixed(1)}
                  </span>
                </td>
                <td className="py-2 px-3 text-center text-slate-300">{p.goals}</td>
                <td className="py-2 px-3 text-center text-slate-300">{p.assists}</td>
                <td className="py-2 px-3 text-center text-white font-bold">{p.piqOvr}</td>
                <td className="py-2 px-3 text-center text-emerald-400 font-medium">{p.piqChange}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* PIQ Development */}
      <div className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
        <h3 className="text-sm font-medium text-white mb-3">Team PIQ Rating Trends</h3>
        <DevelopmentTimeline
          data={[
            { date: 'Sep', ovr: 62 },
            { date: 'Oct', ovr: 65 },
            { date: 'Nov', ovr: 68 },
          ]}
          height={200}
        />
        <p className="text-xs text-slate-500 mt-2">Average team PIQ OVR over the season</p>
      </div>
    </div>
  );
}
