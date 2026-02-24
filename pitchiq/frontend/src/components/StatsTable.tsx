import { useState } from 'react';
import { cn } from '../lib/utils';

interface StatCell {
  value: number;
  dataDensity?: number;
  isExtrapolated?: boolean;
}

interface PlayerRow {
  playerId: number;
  playerName: string;
  jerseyNumber?: number;
  positionPlayed: string;
  screenTimeRatio: number;
  score?: number;
  stats: Record<string, StatCell>;
}

interface StatsTableProps {
  players: PlayerRow[];
  onPlayerClick?: (playerId: number) => void;
}

function DataDensityDot({ density }: { density: number }) {
  const color = density >= 0.7 ? 'bg-emerald-400' : density >= 0.4 ? 'bg-yellow-400' : 'bg-red-400';
  return <span className={cn('inline-block w-1.5 h-1.5 rounded-full ml-1', color)} />;
}

const STAT_COLUMNS = [
  { key: 'touches', label: 'TCH' },
  { key: 'pass_completions', label: 'PAS' },
  { key: 'pass_completion_rate', label: 'PA%', format: (v: number) => `${v.toFixed(0)}%` },
  { key: 'tackles_won', label: 'TKL' },
  { key: 'interceptions', label: 'INT' },
  { key: 'shots', label: 'SHT' },
  { key: 'goals', label: 'G' },
  { key: 'assists', label: 'A' },
  { key: 'dribbles_completed', label: 'DRB' },
  { key: 'distance_covered', label: 'DIST', format: (v: number) => `${v.toFixed(1)}km` },
  { key: 'sprint_count', label: 'SPR' },
];

export default function StatsTable({ players, onPlayerClick }: StatsTableProps) {
  const [sortKey, setSortKey] = useState<string>('score');
  const [sortDesc, setSortDesc] = useState(true);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDesc(!sortDesc);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  const sorted = [...players].sort((a, b) => {
    let aVal: number, bVal: number;
    if (sortKey === 'score') {
      aVal = a.score ?? 0;
      bVal = b.score ?? 0;
    } else if (sortKey === 'screenTime') {
      aVal = a.screenTimeRatio;
      bVal = b.screenTimeRatio;
    } else {
      aVal = a.stats[sortKey]?.value ?? 0;
      bVal = b.stats[sortKey]?.value ?? 0;
    }
    return sortDesc ? bVal - aVal : aVal - bVal;
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            <th className="text-left py-2 px-3 text-slate-400 font-medium">#</th>
            <th className="text-left py-2 px-3 text-slate-400 font-medium">Player</th>
            <th className="text-left py-2 px-3 text-slate-400 font-medium">POS</th>
            <th
              className="text-right py-2 px-3 text-slate-400 font-medium cursor-pointer hover:text-white"
              onClick={() => handleSort('score')}
            >
              Score {sortKey === 'score' && (sortDesc ? '↓' : '↑')}
            </th>
            <th
              className="text-right py-2 px-3 text-slate-400 font-medium cursor-pointer hover:text-white"
              onClick={() => handleSort('screenTime')}
            >
              ST% {sortKey === 'screenTime' && (sortDesc ? '↓' : '↑')}
            </th>
            {STAT_COLUMNS.map((col) => (
              <th
                key={col.key}
                className="text-right py-2 px-3 text-slate-400 font-medium cursor-pointer hover:text-white"
                onClick={() => handleSort(col.key)}
              >
                {col.label} {sortKey === col.key && (sortDesc ? '↓' : '↑')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((player) => {
            const lowScreenTime = player.screenTimeRatio < 0.5;
            return (
              <tr
                key={player.playerId}
                className={cn(
                  'border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors',
                  lowScreenTime && 'bg-orange-500/5',
                )}
                onClick={() => onPlayerClick?.(player.playerId)}
              >
                <td className="py-2 px-3 text-slate-500 font-mono">
                  {player.jerseyNumber ?? '-'}
                </td>
                <td className="py-2 px-3 font-medium text-white">{player.playerName}</td>
                <td className="py-2 px-3 text-slate-400">{player.positionPlayed}</td>
                <td className="py-2 px-3 text-right font-bold">
                  <span className={cn(
                    player.score && player.score >= 7 ? 'text-emerald-400' :
                    player.score && player.score >= 5 ? 'text-blue-400' :
                    'text-slate-400',
                  )}>
                    {player.score?.toFixed(1) ?? '-'}
                  </span>
                </td>
                <td className={cn(
                  'py-2 px-3 text-right',
                  lowScreenTime ? 'text-orange-400' : 'text-slate-400',
                )}>
                  {Math.round(player.screenTimeRatio * 100)}%
                </td>
                {STAT_COLUMNS.map((col) => {
                  const cell = player.stats[col.key];
                  if (!cell) {
                    return <td key={col.key} className="py-2 px-3 text-right text-slate-600">-</td>;
                  }
                  const formatted = col.format ? col.format(cell.value) : cell.value.toFixed(0);
                  return (
                    <td key={col.key} className="py-2 px-3 text-right text-slate-300">
                      {cell.isExtrapolated && <span className="text-slate-500">~</span>}
                      {formatted}
                      {cell.dataDensity !== undefined && <DataDensityDot density={cell.dataDensity} />}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
