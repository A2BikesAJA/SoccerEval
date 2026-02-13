import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { cn } from '../lib/utils';
import PIQCard from '../components/PIQCard';
import PIQRadarChart from '../components/PIQRadarChart';
import PlayerScoreCard from '../components/PlayerScoreCard';
import DevelopmentTimeline from '../components/DevelopmentTimeline';
import WhatIfTool from '../components/WhatIfTool';

// Demo data
const DEMO_PIQ = {
  ovr: 72, spd: 68, sht: 74, pas: 76, drb: 71, def: 42, phy: 63,
  confidenceLevel: 'developing' as const,
  gamesAnalyzed: 8,
};

const DEMO_SCORE = {
  overall: 8.2,
  confidence: 0.92,
  categories: [
    { name: 'Creativity', score: 84, weight: 0.25 },
    { name: 'Goal Threat', score: 78, weight: 0.20 },
    { name: 'Dribbling', score: 72, weight: 0.15 },
    { name: 'Progressive Play', score: 70, weight: 0.15 },
    { name: 'Passing', score: 82, weight: 0.10 },
    { name: 'Work Rate', score: 65, weight: 0.10 },
    { name: 'Discipline', score: 90, weight: 0.05 },
  ],
  bonuses: [
    { event: 'Goal', value: 0.3 },
    { event: 'Goal', value: 0.3 },
    { event: 'Assist', value: 0.2 },
  ],
};

const DEMO_TIMELINE = [
  { date: 'Sep 7', ovr: 65, spd: 62, sht: 68, pas: 70, drb: 64, def: 40, phy: 58 },
  { date: 'Sep 21', ovr: 67, spd: 64, sht: 70, pas: 71, drb: 66, def: 41, phy: 59 },
  { date: 'Oct 5', ovr: 68, spd: 65, sht: 71, pas: 72, drb: 67, def: 41, phy: 60 },
  { date: 'Oct 19', ovr: 69, spd: 66, sht: 72, pas: 73, drb: 68, def: 42, phy: 61 },
  { date: 'Nov 1', ovr: 70, spd: 67, sht: 73, pas: 74, drb: 69, def: 42, phy: 62 },
  { date: 'Nov 8', ovr: 71, spd: 67, sht: 73, pas: 75, drb: 70, def: 42, phy: 62 },
  { date: 'Nov 15', ovr: 72, spd: 68, sht: 74, pas: 76, drb: 71, def: 42, phy: 63 },
];

const SUB_ATTRIBUTES = {
  speed: [
    { name: 'Sprint Speed', value: 70 },
    { name: 'Acceleration', value: 67 },
    { name: 'Off-Ball Movement', value: 72 },
    { name: 'Recovery Runs', value: 60 },
    { name: 'Agility', value: 68 },
  ],
  shooting: [
    { name: 'Finishing', value: 76 },
    { name: 'Shot Power', value: 72 },
    { name: 'Long Shots', value: 68 },
    { name: 'Positioning', value: 78 },
    { name: 'Volleys/Headers', value: 64 },
  ],
  passing: [
    { name: 'Short Passing', value: 80 },
    { name: 'Long Passing', value: 72 },
    { name: 'Crossing', value: 70 },
    { name: 'Vision', value: 82 },
    { name: 'Free Kick Delivery', value: 65 },
  ],
  dribbling: [
    { name: 'Ball Control', value: 74 },
    { name: 'Dribbling', value: 76 },
    { name: 'Composure', value: 70 },
    { name: 'Flair', value: 68 },
    { name: 'Balance', value: 66 },
  ],
  defending: [
    { name: 'Standing Tackle', value: 44 },
    { name: 'Interceptions', value: 46 },
    { name: 'Heading Accuracy', value: 40 },
    { name: 'Marking', value: 38 },
    { name: 'Defensive Awareness', value: 42 },
  ],
  physicality: [
    { name: 'Stamina', value: 66 },
    { name: 'Strength', value: 58 },
    { name: 'Aggression', value: 62 },
    { name: 'Jumping', value: 60 },
  ],
};

function SubAttributeBar({ name, value }: { name: string; value: number }) {
  const color = value >= 75 ? 'bg-emerald-400' : value >= 60 ? 'bg-blue-400' : value >= 45 ? 'bg-yellow-400' : 'bg-slate-500';
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-slate-400 w-36 truncate">{name}</span>
      <div className="flex-1 h-1.5 bg-slate-700/50 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${value}%` }} />
      </div>
      <span className="text-xs font-medium text-slate-300 w-6 text-right">{value}</span>
    </div>
  );
}

export default function PlayerReport() {
  const { playerId } = useParams();
  const [showSubAttributes, setShowSubAttributes] = useState(false);
  const [showTimeline, setShowTimeline] = useState(true);

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Player Report</h1>
        <p className="text-sm text-slate-400 mt-1">Marcus Johnson — #10 CAM</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: PIQ Card + Radar */}
        <div className="space-y-4">
          <PIQCard
            playerName="Marcus Johnson"
            clubName="FC Warriors"
            position="CAM"
            ageGroup="U14"
            competitionTier="ECNL"
            season="2025"
            ovr={DEMO_PIQ.ovr}
            spd={DEMO_PIQ.spd}
            sht={DEMO_PIQ.sht}
            pas={DEMO_PIQ.pas}
            drb={DEMO_PIQ.drb}
            def={DEMO_PIQ.def}
            phy={DEMO_PIQ.phy}
            confidenceLevel={DEMO_PIQ.confidenceLevel}
            gamesAnalyzed={DEMO_PIQ.gamesAnalyzed}
          />

          {/* Competition level context */}
          <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
            <p className="text-xs text-slate-400">
              PIQ Rating: <span className="text-white font-bold">72</span> (ECNL — Tier 1)
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Equivalent to ~86 at State Premier level
            </p>
          </div>

          <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
            <h3 className="text-sm font-medium text-white mb-2">Attribute Radar</h3>
            <PIQRadarChart
              attributes={{
                spd: DEMO_PIQ.spd,
                sht: DEMO_PIQ.sht,
                pas: DEMO_PIQ.pas,
                drb: DEMO_PIQ.drb,
                def: DEMO_PIQ.def,
                phy: DEMO_PIQ.phy,
              }}
              size={250}
            />
          </div>
        </div>

        {/* Middle + Right Columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Game Score */}
          <PlayerScoreCard
            playerName="Marcus Johnson"
            jerseyNumber={10}
            position="CAM"
            score={DEMO_SCORE.overall}
            confidence={DEMO_SCORE.confidence}
            minutesPlayed={82}
            screenTimeRatio={0.78}
            categories={DEMO_SCORE.categories}
            bonuses={DEMO_SCORE.bonuses}
          />

          {/* Sub-Attributes */}
          <div className="bg-slate-800/50 rounded-xl border border-white/10">
            <button
              onClick={() => setShowSubAttributes(!showSubAttributes)}
              className="w-full px-5 py-3 flex items-center justify-between text-sm font-medium text-white hover:bg-white/5 transition-colors"
            >
              <span>29 Sub-Attributes Breakdown</span>
              <span className="text-slate-500">{showSubAttributes ? '−' : '+'}</span>
            </button>
            {showSubAttributes && (
              <div className="px-5 pb-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                {Object.entries(SUB_ATTRIBUTES).map(([category, attrs]) => (
                  <div key={category}>
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                      {category}
                    </h4>
                    <div className="space-y-1.5">
                      {attrs.map((attr) => (
                        <SubAttributeBar key={attr.name} name={attr.name} value={attr.value} />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Development Timeline */}
          <div className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-white">PIQ Development Timeline</h3>
              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className="text-xs text-slate-400 hover:text-white"
              >
                {showTimeline ? 'Show OVR only' : 'Show all attributes'}
              </button>
            </div>
            <DevelopmentTimeline
              data={DEMO_TIMELINE}
              showAttributes={showTimeline}
              height={280}
            />
          </div>

          {/* What If Tool */}
          <WhatIfTool
            playerName="Marcus"
            currentTier={1}
            currentOvr={72}
            currentAttributes={{
              spd: 68, sht: 74, pas: 76, drb: 71, def: 42, phy: 63,
            }}
            onSimulate={async (targetTier) => ({
              estimatedOvr: Math.round(72 * (1 + (targetTier - 1) * 0.08)),
              estimatedAttributes: {},
              tierName: ['', 'Elite', 'National', 'High National', 'NPL', 'State Premier', 'Travel', 'Rec+', 'Rec'][targetTier],
            })}
          />
        </div>
      </div>
    </div>
  );
}
