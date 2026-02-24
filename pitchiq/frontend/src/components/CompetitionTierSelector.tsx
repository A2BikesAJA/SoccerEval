import { cn } from '../lib/utils';

interface CompetitionTierSelectorProps {
  value: number;
  onChange: (tier: number) => void;
}

const TIERS = [
  { value: 1, name: 'Tier 1 — Elite', desc: 'MLS NEXT (MLS Academy) / ECNL', multiplier: 1.0 },
  { value: 2, name: 'Tier 2 — National', desc: 'MLS NEXT (non-MLS) / Girls Academy', multiplier: 0.95 },
  { value: 3, name: 'Tier 3 — High National', desc: 'ECRL / NAL / GA Aspire / DPL', multiplier: 0.88 },
  { value: 4, name: 'Tier 4 — National/Regional', desc: 'NPL / USYS National League', multiplier: 0.80 },
  { value: 5, name: 'Tier 5 — State Premier', desc: 'State Premier League / Presidents League', multiplier: 0.72 },
  { value: 6, name: 'Tier 6 — Competitive Travel', desc: 'Club travel / competitive select', multiplier: 0.62 },
  { value: 7, name: 'Tier 7 — Recreational+', desc: 'Advanced rec / town travel', multiplier: 0.50 },
  { value: 8, name: 'Tier 8 — Recreational', desc: 'Recreational leagues', multiplier: 0.40 },
];

export default function CompetitionTierSelector({ value, onChange }: CompetitionTierSelectorProps) {
  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-slate-300">Competition Tier</label>
      <div className="space-y-1">
        {TIERS.map((tier) => (
          <button
            key={tier.value}
            type="button"
            onClick={() => onChange(tier.value)}
            className={cn(
              'w-full text-left px-3 py-2 rounded-lg border transition-all text-sm',
              value === tier.value
                ? 'border-emerald-500 bg-emerald-900/20 text-white'
                : 'border-slate-700 bg-slate-800/50 text-slate-400 hover:border-slate-600',
            )}
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="font-medium">{tier.name}</span>
                <span className="text-xs text-slate-500 ml-2">{tier.desc}</span>
              </div>
              <span className="text-xs text-slate-500 font-mono">×{tier.multiplier.toFixed(2)}</span>
            </div>
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        The competition tier determines how your players' PIQ Ratings compare against the broader youth soccer population.
        A higher tier means stronger competition context.
      </p>
    </div>
  );
}
