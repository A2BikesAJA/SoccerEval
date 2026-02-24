import { cn } from '../lib/utils';

interface ScreenTimeIndicatorProps {
  ratio: number;
  adjustedRatio?: number;
  showLabel?: boolean;
  size?: 'sm' | 'md';
}

export default function ScreenTimeIndicator({
  ratio,
  adjustedRatio,
  showLabel = true,
  size = 'sm',
}: ScreenTimeIndicatorProps) {
  const pct = Math.round(ratio * 100);
  const adjustedPct = adjustedRatio ? Math.round(adjustedRatio * 100) : undefined;

  const color = pct >= 70 ? 'text-emerald-400' : pct >= 40 ? 'text-yellow-400' : 'text-red-400';
  const bgColor = pct >= 70 ? 'bg-emerald-400' : pct >= 40 ? 'bg-yellow-400' : 'bg-red-400';

  return (
    <div className={cn('inline-flex items-center gap-1.5', size === 'md' && 'gap-2')}>
      <div className={cn(
        'rounded-full',
        size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2',
        bgColor,
      )} />
      {showLabel && (
        <span className={cn(
          'font-medium',
          size === 'sm' ? 'text-xs' : 'text-sm',
          color,
        )}>
          {pct}% screen time
          {adjustedPct && adjustedPct !== pct && (
            <span className="text-slate-500"> ({adjustedPct}% adjusted)</span>
          )}
        </span>
      )}
    </div>
  );
}
