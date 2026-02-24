import { useState } from 'react';
import { cn } from '../lib/utils';

interface WhatIfToolProps {
  playerName: string;
  currentTier: number;
  currentOvr: number;
  currentAttributes: {
    spd: number; sht: number; pas: number;
    drb: number; def: number; phy: number;
  };
  onSimulate: (targetTier: number) => Promise<{
    estimatedOvr: number;
    estimatedAttributes: Record<string, number>;
    tierName: string;
  }>;
}

const TIER_NAMES: Record<number, string> = {
  1: 'Elite (MLS NEXT/ECNL)',
  2: 'National (GA)',
  3: 'High National (ECRL/DPL)',
  4: 'National/Regional (NPL)',
  5: 'State Premier',
  6: 'Competitive Travel',
  7: 'Recreational+',
  8: 'Recreational',
};

export default function WhatIfTool({
  playerName,
  currentTier,
  currentOvr,
  currentAttributes: _currentAttributes,
  onSimulate,
}: WhatIfToolProps) {
  const [targetTier, setTargetTier] = useState(Math.max(1, currentTier - 1));
  const [result, setResult] = useState<{
    estimatedOvr: number;
    estimatedAttributes: Record<string, number>;
    tierName: string;
  } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const res = await onSimulate(targetTier);
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  const ovrDiff = result ? result.estimatedOvr - currentOvr : 0;

  return (
    <div className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
      <h3 className="text-sm font-bold text-white mb-1">"What If" Rating Simulator</h3>
      <p className="text-xs text-slate-400 mb-4">
        See what {playerName}'s rating would be at a different competition level.
      </p>

      <div className="flex items-end gap-3 mb-4">
        <div className="flex-1">
          <label className="block text-xs text-slate-400 mb-1">Target Competition Tier</label>
          <select
            value={targetTier}
            onChange={(e) => { setTargetTier(Number(e.target.value)); setResult(null); }}
            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
          >
            {Object.entries(TIER_NAMES).map(([val, name]) => (
              <option key={val} value={val} disabled={Number(val) === currentTier}>
                {name} {Number(val) === currentTier ? '(current)' : ''}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={handleSimulate}
          disabled={loading || targetTier === currentTier}
          className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 rounded-lg text-sm text-white font-medium transition-colors"
        >
          {loading ? 'Simulating...' : 'Simulate'}
        </button>
      </div>

      {result && (
        <div className="border-t border-white/10 pt-4">
          <div className="flex items-center gap-4 mb-3">
            <div className="text-center">
              <div className="text-xs text-slate-500 mb-1">Current ({TIER_NAMES[currentTier]?.split(' ')[0]})</div>
              <div className="text-2xl font-black text-white">{currentOvr}</div>
            </div>
            <div className="text-slate-500 text-lg">→</div>
            <div className="text-center">
              <div className="text-xs text-slate-500 mb-1">At {result.tierName.split(' ')[0]}</div>
              <div className={cn(
                'text-2xl font-black',
                ovrDiff > 0 ? 'text-emerald-400' : ovrDiff < 0 ? 'text-red-400' : 'text-white',
              )}>
                {result.estimatedOvr}
              </div>
            </div>
            <div className={cn(
              'text-sm font-bold',
              ovrDiff > 0 ? 'text-emerald-400' : ovrDiff < 0 ? 'text-red-400' : 'text-slate-500',
            )}>
              {ovrDiff > 0 ? '+' : ''}{ovrDiff}
            </div>
          </div>

          <div className="text-xs text-slate-400">
            {targetTier > currentTier
              ? `At a lower competition level, ${playerName}'s rating would increase because the same performance is relatively stronger.`
              : `At a higher competition level, ${playerName}'s rating would decrease because the same performance faces stronger competition.`
            }
          </div>
        </div>
      )}
    </div>
  );
}
