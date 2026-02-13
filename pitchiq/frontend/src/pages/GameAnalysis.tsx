import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { cn } from '../lib/utils';
import StatsTable from '../components/StatsTable';
import TeamComparison from '../components/TeamComparison';
import HeatMap from '../components/HeatMap';
import ProcessingStatus from '../components/ProcessingStatus';

// Demo data
const DEMO_TEAM_STATS = [
  { label: 'Possession', home: 58, away: 42, format: (v: number) => `${v}%` },
  { label: 'Shots', home: 14, away: 8 },
  { label: 'Shots on Target', home: 7, away: 3 },
  { label: 'Passes', home: 245, away: 189 },
  { label: 'Pass Accuracy', home: 76, away: 68, format: (v: number) => `${v}%` },
  { label: 'Tackles', home: 18, away: 22 },
  { label: 'Interceptions', home: 12, away: 9 },
  { label: 'Fouls', home: 8, away: 11, higherIsBetter: false },
  { label: 'Corners', home: 5, away: 2 },
  { label: 'Distance (km)', home: 42.5, away: 39.8, format: (v: number) => v.toFixed(1) },
];

const DEMO_PLAYERS = [
  {
    playerId: 1, playerName: 'Marcus Johnson', jerseyNumber: 10, positionPlayed: 'CAM',
    screenTimeRatio: 0.78, score: 8.2,
    stats: {
      touches: { value: 52, dataDensity: 0.78 },
      pass_completions: { value: 28, dataDensity: 0.78 },
      pass_completion_rate: { value: 82, dataDensity: 0.78 },
      tackles_won: { value: 3, dataDensity: 0.78 },
      interceptions: { value: 2, dataDensity: 0.78 },
      shots: { value: 4, dataDensity: 0.78 },
      goals: { value: 2, dataDensity: 0.78 },
      assists: { value: 1, dataDensity: 0.78 },
      dribbles_completed: { value: 5, dataDensity: 0.78 },
      distance_covered: { value: 7.2, dataDensity: 0.78 },
      sprint_count: { value: 14, dataDensity: 0.78 },
    },
  },
  {
    playerId: 2, playerName: 'David Kim', jerseyNumber: 6, positionPlayed: 'CDM',
    screenTimeRatio: 0.72, score: 7.4,
    stats: {
      touches: { value: 48, dataDensity: 0.72 },
      pass_completions: { value: 32, dataDensity: 0.72 },
      pass_completion_rate: { value: 86, dataDensity: 0.72 },
      tackles_won: { value: 6, dataDensity: 0.72 },
      interceptions: { value: 5, dataDensity: 0.72 },
      shots: { value: 1, dataDensity: 0.72 },
      goals: { value: 0, dataDensity: 0.72 },
      assists: { value: 0, dataDensity: 0.72 },
      dribbles_completed: { value: 2, dataDensity: 0.72 },
      distance_covered: { value: 8.1, dataDensity: 0.72 },
      sprint_count: { value: 11, dataDensity: 0.72 },
    },
  },
  {
    playerId: 3, playerName: 'Alex Rivera', jerseyNumber: 9, positionPlayed: 'ST',
    screenTimeRatio: 0.65, score: 7.8,
    stats: {
      touches: { value: 31, dataDensity: 0.65 },
      pass_completions: { value: 14, dataDensity: 0.65 },
      pass_completion_rate: { value: 70, dataDensity: 0.65 },
      tackles_won: { value: 1, dataDensity: 0.65 },
      interceptions: { value: 0, dataDensity: 0.65 },
      shots: { value: 5, dataDensity: 0.65 },
      goals: { value: 1, dataDensity: 0.65 },
      assists: { value: 0, dataDensity: 0.65 },
      dribbles_completed: { value: 3, dataDensity: 0.65 },
      distance_covered: { value: 6.5, dataDensity: 0.65 },
      sprint_count: { value: 16, dataDensity: 0.65 },
    },
  },
  {
    playerId: 4, playerName: 'Chris Taylor', jerseyNumber: 4, positionPlayed: 'CB',
    screenTimeRatio: 0.38, score: 6.5,
    stats: {
      touches: { value: 22, dataDensity: 0.38 },
      pass_completions: { value: 18, dataDensity: 0.38 },
      pass_completion_rate: { value: 78, dataDensity: 0.38 },
      tackles_won: { value: 4, dataDensity: 0.38 },
      interceptions: { value: 3, dataDensity: 0.38 },
      shots: { value: 0, dataDensity: 0.38 },
      goals: { value: 0, dataDensity: 0.38 },
      assists: { value: 0, dataDensity: 0.38 },
      dribbles_completed: { value: 0, dataDensity: 0.38 },
      distance_covered: { value: 3.8, dataDensity: 0.38, isExtrapolated: true },
      sprint_count: { value: 5, dataDensity: 0.38 },
    },
  },
];

export default function GameAnalysis() {
  const { gameId } = useParams();
  const [selectedPlayer, setSelectedPlayer] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'players' | 'heatmap'>('overview');

  // Demo positions for heatmap
  const demoPositions = Array.from({ length: 100 }, () => ({
    x: 0.3 + Math.random() * 0.4,
    y: 0.2 + Math.random() * 0.6,
    intensity: Math.random(),
  }));

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Game Analysis</h1>
          <p className="text-sm text-slate-400 mt-1">
            FC Warriors vs FC Lightning — Nov 15, 2025
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-2xl font-black text-white">3 - 1</span>
        </div>
      </div>

      {/* Camera source banner */}
      <div className="mb-4 p-3 bg-amber-900/10 border border-amber-800/20 rounded-lg flex items-center gap-2">
        <span className="text-amber-400 text-xs font-medium">VEO Follow Cam</span>
        <span className="text-xs text-amber-300/60">
          Estimated 45% field coverage. Stats for off-ball players may have lower confidence.
        </span>
      </div>

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
          <TeamComparison
            homeTeam="FC Warriors"
            awayTeam="FC Lightning"
            stats={DEMO_TEAM_STATS}
          />
          <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
            <h3 className="text-sm font-medium text-white mb-3">Key Events</h3>
            <div className="space-y-2">
              {[
                { time: "12'", event: "Goal — Marcus Johnson (Assist: Alex Rivera)", type: 'goal' },
                { time: "28'", event: "Goal — Alex Rivera", type: 'goal' },
                { time: "41'", event: "Yellow Card — David Kim (Foul)", type: 'card' },
                { time: "55'", event: "Goal conceded — Opponent #7", type: 'conceded' },
                { time: "72'", event: "Goal — Marcus Johnson", type: 'goal' },
              ].map((evt, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <span className="text-slate-500 font-mono w-10">{evt.time}</span>
                  <div className={cn(
                    'w-2 h-2 rounded-full',
                    evt.type === 'goal' ? 'bg-emerald-400' :
                    evt.type === 'card' ? 'bg-yellow-400' :
                    'bg-red-400',
                  )} />
                  <span className="text-slate-300">{evt.event}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Players Tab */}
      {activeTab === 'players' && (
        <div>
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
            players={DEMO_PLAYERS}
            onPlayerClick={(id) => setSelectedPlayer(id)}
          />
        </div>
      )}

      {/* Heatmap Tab */}
      {activeTab === 'heatmap' && (
        <div>
          <div className="mb-4">
            <select className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm">
              <option>Marcus Johnson (#10)</option>
              <option>David Kim (#6)</option>
              <option>Alex Rivera (#9)</option>
              <option>Chris Taylor (#4)</option>
            </select>
          </div>
          <HeatMap
            positions={demoPositions}
            playerName="Marcus Johnson"
            unobservedZones={[
              { x: 0, y: 0, w: 0.15, h: 1.0 },
              { x: 0.85, y: 0, w: 0.15, h: 1.0 },
            ]}
          />
        </div>
      )}
    </div>
  );
}
