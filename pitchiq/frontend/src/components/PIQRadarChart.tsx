import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from 'recharts';

interface PIQRadarChartProps {
  attributes: {
    spd: number;
    sht: number;
    pas: number;
    drb: number;
    def: number;
    phy: number;
  };
  compareAttributes?: {
    spd: number;
    sht: number;
    pas: number;
    drb: number;
    def: number;
    phy: number;
  };
  playerName?: string;
  compareName?: string;
  size?: number;
}

export default function PIQRadarChart({
  attributes,
  compareAttributes,
  playerName = 'Player',
  compareName = 'Compare',
  size = 300,
}: PIQRadarChartProps) {
  const data = [
    { attribute: 'SPD', player: attributes.spd, compare: compareAttributes?.spd },
    { attribute: 'SHT', player: attributes.sht, compare: compareAttributes?.sht },
    { attribute: 'PAS', player: attributes.pas, compare: compareAttributes?.pas },
    { attribute: 'DRB', player: attributes.drb, compare: compareAttributes?.drb },
    { attribute: 'DEF', player: attributes.def, compare: compareAttributes?.def },
    { attribute: 'PHY', player: attributes.phy, compare: compareAttributes?.phy },
  ];

  return (
    <ResponsiveContainer width="100%" height={size}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="80%">
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis
          dataKey="attribute"
          tick={{ fill: '#94a3b8', fontSize: 12, fontWeight: 600 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 99]}
          tick={{ fill: '#475569', fontSize: 10 }}
          tickCount={5}
        />
        <Radar
          name={playerName}
          dataKey="player"
          stroke="#22c55e"
          fill="#22c55e"
          fillOpacity={0.2}
          strokeWidth={2}
        />
        {compareAttributes && (
          <Radar
            name={compareName}
            dataKey="compare"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.15}
            strokeWidth={2}
            strokeDasharray="4 4"
          />
        )}
        {compareAttributes && <Legend />}
      </RadarChart>
    </ResponsiveContainer>
  );
}
