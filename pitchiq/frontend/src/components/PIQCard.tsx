import { cn } from '../lib/utils';

interface PIQCardProps {
  playerName: string;
  clubName: string;
  position: string;
  ageGroup: string;
  competitionTier: string;
  season?: string;
  photoUrl?: string;
  ovr: number;
  spd: number;
  sht: number;
  pas: number;
  drb: number;
  def: number;
  phy: number;
  confidenceLevel: 'calculating' | 'preliminary' | 'developing' | 'established';
  gamesAnalyzed: number;
  className?: string;
}

function getOvrColor(ovr: number): string {
  if (ovr >= 80) return 'from-yellow-400 to-amber-500';
  if (ovr >= 70) return 'from-emerald-400 to-green-500';
  if (ovr >= 60) return 'from-blue-400 to-cyan-500';
  if (ovr >= 50) return 'from-purple-400 to-violet-500';
  return 'from-slate-400 to-slate-500';
}

function getOvrLabel(ovr: number): string {
  if (ovr >= 85) return 'Elite';
  if (ovr >= 75) return 'Excellent';
  if (ovr >= 65) return 'Strong';
  if (ovr >= 55) return 'Solid';
  if (ovr >= 45) return 'Developing';
  if (ovr >= 35) return 'Growing';
  return 'Building';
}

function getAttributeBarWidth(value: number): string {
  return `${Math.min(99, Math.max(1, value))}%`;
}

function getAttributeColor(value: number): string {
  if (value >= 80) return 'bg-yellow-400';
  if (value >= 70) return 'bg-emerald-400';
  if (value >= 60) return 'bg-blue-400';
  if (value >= 50) return 'bg-purple-400';
  return 'bg-slate-400';
}

export default function PIQCard({
  playerName,
  clubName,
  position,
  ageGroup,
  competitionTier,
  season = '2025',
  photoUrl,
  ovr,
  spd, sht, pas, drb, def: defVal, phy,
  confidenceLevel,
  gamesAnalyzed,
  className,
}: PIQCardProps) {
  const isCalculating = confidenceLevel === 'calculating';
  const attributes = [
    { label: 'SPD', value: spd },
    { label: 'SHT', value: sht },
    { label: 'PAS', value: pas },
    { label: 'DRB', value: drb },
    { label: 'DEF', value: defVal },
    { label: 'PHY', value: phy },
  ];

  return (
    <div className={cn(
      'relative w-72 rounded-2xl overflow-hidden shadow-2xl border border-white/10',
      'bg-gradient-to-b from-slate-800 to-slate-900',
      className,
    )}>
      {/* Top gradient accent */}
      <div className={cn('h-1.5 bg-gradient-to-r', getOvrColor(ovr))} />

      {/* Header */}
      <div className="px-5 pt-4 pb-2 flex items-start gap-4">
        {/* Photo / Avatar */}
        <div className="w-20 h-20 rounded-xl overflow-hidden bg-slate-700 flex-shrink-0 border border-white/10">
          {photoUrl ? (
            <img src={photoUrl} alt={playerName} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-slate-400 text-2xl font-bold">
              {playerName.charAt(0)}
            </div>
          )}
        </div>

        {/* OVR + Position */}
        <div className="flex-1 min-w-0">
          {isCalculating ? (
            <div>
              <div className="text-sm text-slate-400 mb-1">Calculating...</div>
              <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all"
                  style={{ width: `${(gamesAnalyzed / 3) * 100}%` }}
                />
              </div>
              <div className="text-xs text-slate-500 mt-1">
                {gamesAnalyzed}/3 games analyzed
              </div>
            </div>
          ) : (
            <>
              <div className={cn(
                'text-4xl font-black bg-gradient-to-r bg-clip-text text-transparent',
                getOvrColor(ovr),
              )}>
                {ovr}
              </div>
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">
                {getOvrLabel(ovr)}
              </div>
              <div className="text-xs text-slate-500 mt-0.5">
                {position} · {ageGroup} · {competitionTier}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Divider */}
      <div className="mx-5 h-px bg-white/10" />

      {/* Attributes */}
      <div className="px-5 py-3 space-y-2">
        {attributes.map((attr) => (
          <div key={attr.label} className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-400 w-8">{attr.label}</span>
            <div className="flex-1 h-2 bg-slate-700/50 rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-500', getAttributeColor(attr.value))}
                style={{ width: isCalculating ? '0%' : getAttributeBarWidth(attr.value) }}
              />
            </div>
            <span className={cn(
              'text-xs font-bold w-6 text-right',
              isCalculating ? 'text-slate-600' : 'text-slate-300',
            )}>
              {isCalculating ? '--' : attr.value}
            </span>
          </div>
        ))}
      </div>

      {/* Divider */}
      <div className="mx-5 h-px bg-white/10" />

      {/* Footer */}
      <div className="px-5 py-3">
        <div className="text-sm font-semibold text-white truncate">{playerName}</div>
        <div className="text-xs text-slate-400">{clubName}</div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-xs text-slate-500">Season {season}</span>
          <span className={cn(
            'text-xs px-2 py-0.5 rounded-full font-medium',
            confidenceLevel === 'established' ? 'bg-emerald-900/50 text-emerald-400' :
            confidenceLevel === 'developing' ? 'bg-blue-900/50 text-blue-400' :
            confidenceLevel === 'preliminary' ? 'bg-amber-900/50 text-amber-400' :
            'bg-slate-700 text-slate-400',
          )}>
            {confidenceLevel === 'calculating' ? `${gamesAnalyzed}/3 games` :
             confidenceLevel === 'preliminary' ? 'Preliminary' :
             confidenceLevel === 'developing' ? 'Developing' : 'Established'}
          </span>
        </div>
      </div>
    </div>
  );
}
