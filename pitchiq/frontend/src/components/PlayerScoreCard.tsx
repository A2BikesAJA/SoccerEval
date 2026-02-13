import { cn } from '../lib/utils';

interface CategoryScore {
  name: string;
  score: number;
  weight: number;
}

interface PlayerScoreCardProps {
  playerName: string;
  jerseyNumber?: number;
  position: string;
  score: number;
  confidence: number;
  minutesPlayed: number;
  screenTimeRatio: number;
  categories: CategoryScore[];
  bonuses?: { event: string; value: number }[];
}

function getScoreColor(score: number): string {
  if (score >= 8.0) return 'text-yellow-400';
  if (score >= 7.0) return 'text-emerald-400';
  if (score >= 6.0) return 'text-blue-400';
  if (score >= 5.0) return 'text-purple-400';
  return 'text-slate-400';
}

function getScoreBg(score: number): string {
  if (score >= 8.0) return 'from-yellow-500/20 to-amber-500/10';
  if (score >= 7.0) return 'from-emerald-500/20 to-green-500/10';
  if (score >= 6.0) return 'from-blue-500/20 to-cyan-500/10';
  if (score >= 5.0) return 'from-purple-500/20 to-violet-500/10';
  return 'from-slate-500/20 to-slate-600/10';
}

export default function PlayerScoreCard({
  playerName,
  jerseyNumber,
  position,
  score,
  confidence,
  minutesPlayed,
  screenTimeRatio,
  categories,
  bonuses = [],
}: PlayerScoreCardProps) {
  const screenTimePct = Math.round(screenTimeRatio * 100);

  return (
    <div className="bg-slate-800/50 rounded-xl border border-white/10 overflow-hidden">
      {/* Header */}
      <div className={cn('p-4 bg-gradient-to-r', getScoreBg(score))}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              {jerseyNumber !== undefined && (
                <span className="text-sm font-bold text-slate-400">#{jerseyNumber}</span>
              )}
              <h3 className="text-lg font-bold text-white">{playerName}</h3>
            </div>
            <span className="text-xs text-slate-400 uppercase tracking-wider">{position}</span>
          </div>
          <div className="text-right">
            <div className={cn('text-3xl font-black', getScoreColor(score))}>
              {score.toFixed(1)}
            </div>
            <div className="text-xs text-slate-400">
              {confidence < 1.0 ? `${Math.round(confidence * 100)}% confidence` : 'Full match'}
            </div>
          </div>
        </div>

        {/* Meta info */}
        <div className="flex gap-4 mt-2 text-xs text-slate-400">
          <span>{minutesPlayed.toFixed(0)} min played</span>
          <span className={cn(
            screenTimePct < 50 ? 'text-orange-400' : 'text-slate-400',
          )}>
            {screenTimePct}% screen time
          </span>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="p-4 space-y-2">
        {categories.map((cat) => (
          <div key={cat.name} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-32 truncate">{cat.name}</span>
            <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-green-400 rounded-full"
                style={{ width: `${Math.min(100, cat.score)}%` }}
              />
            </div>
            <span className="text-xs font-medium text-slate-300 w-8 text-right">
              {cat.score.toFixed(0)}
            </span>
            <span className="text-xs text-slate-500 w-6 text-right">
              ×{cat.weight.toFixed(2)}
            </span>
          </div>
        ))}
      </div>

      {/* Bonuses */}
      {bonuses.length > 0 && (
        <div className="px-4 pb-3">
          <div className="flex flex-wrap gap-1.5">
            {bonuses.map((bonus, i) => (
              <span
                key={i}
                className={cn(
                  'text-xs px-2 py-0.5 rounded-full font-medium',
                  bonus.value > 0 ? 'bg-emerald-900/50 text-emerald-400' : 'bg-red-900/50 text-red-400',
                )}
              >
                {bonus.event} {bonus.value > 0 ? '+' : ''}{bonus.value.toFixed(1)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
