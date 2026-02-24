import PIQCard from './PIQCard';
import PIQRadarChart from './PIQRadarChart';

interface PlayerData {
  playerName: string;
  clubName: string;
  position: string;
  ageGroup: string;
  competitionTier: string;
  ovr: number;
  spd: number;
  sht: number;
  pas: number;
  drb: number;
  def: number;
  phy: number;
  confidenceLevel: 'calculating' | 'preliminary' | 'developing' | 'established';
  gamesAnalyzed: number;
}

interface PlayerComparisonProps {
  players: PlayerData[];
}

export default function PlayerComparison({ players }: PlayerComparisonProps) {
  if (players.length < 2) return null;

  return (
    <div>
      {/* Cards side by side */}
      <div className="flex flex-wrap gap-4 justify-center mb-6">
        {players.map((p, i) => (
          <PIQCard key={i} {...p} />
        ))}
      </div>

      {/* Overlaid radar */}
      {players.length === 2 && (
        <div className="bg-slate-800/50 rounded-xl border border-white/10 p-4">
          <h3 className="text-sm font-medium text-slate-300 mb-2">Attribute Comparison</h3>
          <PIQRadarChart
            attributes={{
              spd: players[0].spd,
              sht: players[0].sht,
              pas: players[0].pas,
              drb: players[0].drb,
              def: players[0].def,
              phy: players[0].phy,
            }}
            compareAttributes={{
              spd: players[1].spd,
              sht: players[1].sht,
              pas: players[1].pas,
              drb: players[1].drb,
              def: players[1].def,
              phy: players[1].phy,
            }}
            playerName={players[0].playerName}
            compareName={players[1].playerName}
            size={350}
          />
        </div>
      )}

      {/* Attribute table comparison */}
      <div className="mt-4 bg-slate-800/50 rounded-xl border border-white/10 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th className="py-2 px-3 text-left text-slate-400">Attribute</th>
              {players.map((p, i) => (
                <th key={i} className="py-2 px-3 text-right text-slate-400">{p.playerName}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {['SPD', 'SHT', 'PAS', 'DRB', 'DEF', 'PHY'].map((attr) => {
              const key = attr.toLowerCase() as 'spd' | 'sht' | 'pas' | 'drb' | 'def' | 'phy';
              const values = players.map((p) => p[key]);
              const max = Math.max(...values);
              return (
                <tr key={attr} className="border-b border-white/5">
                  <td className="py-2 px-3 text-slate-300 font-medium">{attr}</td>
                  {values.map((val, i) => (
                    <td key={i} className={`py-2 px-3 text-right font-bold ${val === max ? 'text-emerald-400' : 'text-slate-400'}`}>
                      {val}
                    </td>
                  ))}
                </tr>
              );
            })}
            <tr className="bg-white/5">
              <td className="py-2 px-3 text-white font-bold">OVR</td>
              {players.map((p, i) => {
                const max = Math.max(...players.map((x) => x.ovr));
                return (
                  <td key={i} className={`py-2 px-3 text-right font-black text-lg ${p.ovr === max ? 'text-emerald-400' : 'text-slate-300'}`}>
                    {p.ovr}
                  </td>
                );
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
