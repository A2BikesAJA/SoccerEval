import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { playersApi, piqApi } from '../lib/api';
import { cn } from '../lib/utils';
import PIQCard from '../components/PIQCard';
import PIQRadarChart from '../components/PIQRadarChart';
import DevelopmentTimeline from '../components/DevelopmentTimeline';

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
  const [player, setPlayer] = useState<any>(null);
  const [piq, setPiq] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!playerId) return;
    const id = Number(playerId);
    Promise.all([
      playersApi.get(id).then((r) => r.data).catch(() => null),
      piqApi.getPlayerRating(id).then((r) => r.data).catch(() => null),
      piqApi.getPlayerHistory(id).then((r) => r.data).catch(() => []),
    ])
      .then(([p, q, h]) => {
        setPlayer(p);
        setPiq(q);
        setHistory(h);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [playerId]);

  if (loading) {
    return <div className="text-center py-16 text-slate-500">Loading player data...</div>;
  }

  if (!player) {
    return (
      <div className="text-center py-16">
        <h2 className="text-lg font-medium text-white mb-2">Player not found</h2>
        <p className="text-sm text-slate-400 mb-4">This player does not exist or has no data yet.</p>
        <Link to="/" className="text-emerald-400 hover:text-emerald-300 text-sm">Back to Dashboard</Link>
      </div>
    );
  }

  const hasPiq = piq && piq.ovr;

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Player Report</h1>
        <p className="text-sm text-slate-400 mt-1">
          {player.name} — #{player.jersey_number} {player.position || ''}
        </p>
      </div>

      {!hasPiq ? (
        <div className="text-center py-16 bg-slate-800/50 rounded-xl border border-white/10">
          <h2 className="text-lg font-medium text-white mb-2">No PIQ Rating Yet</h2>
          <p className="text-sm text-slate-400">
            Upload and process game footage to generate this player's PIQ rating and analytics.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: PIQ Card + Radar */}
          <div className="space-y-4">
            <PIQCard
              playerName={player.name}
              clubName=""
              position={player.position || ''}
              ageGroup=""
              competitionTier=""
              season=""
              ovr={piq.ovr}
              spd={piq.spd || 0}
              sht={piq.sht || 0}
              pas={piq.pas || 0}
              drb={piq.drb || 0}
              def={piq.def || 0}
              phy={piq.phy || 0}
              confidenceLevel={piq.confidence_level || 'developing'}
              gamesAnalyzed={piq.games_analyzed_count || 0}
            />

            <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
              <h3 className="text-sm font-medium text-white mb-2">Attribute Radar</h3>
              <PIQRadarChart
                attributes={{
                  spd: piq.spd || 0,
                  sht: piq.sht || 0,
                  pas: piq.pas || 0,
                  drb: piq.drb || 0,
                  def: piq.def || 0,
                  phy: piq.phy || 0,
                }}
                size={250}
              />
            </div>
          </div>

          {/* Middle + Right Columns */}
          <div className="lg:col-span-2 space-y-6">
            {/* Sub-Attributes */}
            {piq.sub_attributes && (
              <div className="bg-slate-800/50 rounded-xl border border-white/10">
                <button
                  onClick={() => setShowSubAttributes(!showSubAttributes)}
                  className="w-full px-5 py-3 flex items-center justify-between text-sm font-medium text-white hover:bg-white/5 transition-colors"
                >
                  <span>Sub-Attributes Breakdown</span>
                  <span className="text-slate-500">{showSubAttributes ? '−' : '+'}</span>
                </button>
                {showSubAttributes && (
                  <div className="px-5 pb-4 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {Object.entries(piq.sub_attributes).map(([category, attrs]: [string, any]) => (
                      <div key={category}>
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
                          {category}
                        </h4>
                        <div className="space-y-1.5">
                          {Array.isArray(attrs) && attrs.map((attr: any) => (
                            <SubAttributeBar key={attr.name} name={attr.name} value={attr.value} />
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Development Timeline */}
            {history.length > 0 && (
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
                  data={history}
                  showAttributes={showTimeline}
                  height={280}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
