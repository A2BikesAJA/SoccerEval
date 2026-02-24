import { cn } from '../lib/utils';

interface TeamStat {
  label: string;
  home: number;
  away: number;
  format?: (v: number) => string;
  higherIsBetter?: boolean;
}

interface TeamComparisonProps {
  homeTeam: string;
  awayTeam: string;
  stats: TeamStat[];
}

export default function TeamComparison({ homeTeam, awayTeam, stats }: TeamComparisonProps) {
  return (
    <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-bold text-white">{homeTeam}</span>
        <span className="text-xs text-slate-500 uppercase tracking-wider">VS</span>
        <span className="text-sm font-bold text-white">{awayTeam}</span>
      </div>

      {/* Stats */}
      <div className="space-y-3">
        {stats.map((stat) => {
          const total = stat.home + stat.away || 1;
          const homePct = (stat.home / total) * 100;
          const awayPct = (stat.away / total) * 100;
          const higherBetter = stat.higherIsBetter !== false;
          const homeWins = higherBetter ? stat.home > stat.away : stat.home < stat.away;
          const awayWins = higherBetter ? stat.away > stat.home : stat.away < stat.home;
          const fmt = stat.format || ((v: number) => v.toFixed(0));

          return (
            <div key={stat.label}>
              <div className="flex justify-between text-xs mb-1">
                <span className={cn('font-medium', homeWins ? 'text-emerald-400' : 'text-slate-400')}>
                  {fmt(stat.home)}
                </span>
                <span className="text-slate-500">{stat.label}</span>
                <span className={cn('font-medium', awayWins ? 'text-emerald-400' : 'text-slate-400')}>
                  {fmt(stat.away)}
                </span>
              </div>
              <div className="flex h-2 gap-1 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'rounded-l-full transition-all',
                    homeWins ? 'bg-emerald-500' : 'bg-slate-600',
                  )}
                  style={{ width: `${homePct}%` }}
                />
                <div
                  className={cn(
                    'rounded-r-full transition-all',
                    awayWins ? 'bg-emerald-500' : 'bg-slate-600',
                  )}
                  style={{ width: `${awayPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
