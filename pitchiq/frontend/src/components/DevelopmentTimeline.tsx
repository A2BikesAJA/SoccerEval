import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TimelineDataPoint {
  date: string;
  ovr: number;
  spd?: number;
  sht?: number;
  pas?: number;
  drb?: number;
  def?: number;
  phy?: number;
}

interface DevelopmentTimelineProps {
  data: TimelineDataPoint[];
  showAttributes?: boolean;
  height?: number;
}

const ATTRIBUTE_COLORS: Record<string, string> = {
  ovr: '#22c55e',
  spd: '#f59e0b',
  sht: '#ef4444',
  pas: '#3b82f6',
  drb: '#a855f7',
  def: '#06b6d4',
  phy: '#f97316',
};

export default function DevelopmentTimeline({
  data,
  showAttributes = false,
  height = 300,
}: DevelopmentTimelineProps) {
  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-500 text-sm">
        Not enough data to display trends yet.
      </div>
    );
  }

  // Calculate growth
  const firstOvr = data[0]?.ovr ?? 0;
  const lastOvr = data[data.length - 1]?.ovr ?? 0;
  const growth = lastOvr - firstOvr;

  return (
    <div>
      {data.length >= 2 && (
        <div className="flex items-center gap-2 mb-3">
          <span className={growth >= 0 ? 'text-emerald-400' : 'text-red-400'}>
            {growth >= 0 ? '↑' : '↓'} {Math.abs(growth)} OVR
          </span>
          <span className="text-xs text-slate-500">
            {data[0].date} → {data[data.length - 1].date}
          </span>
        </div>
      )}

      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
          />
          <YAxis
            domain={[0, 99]}
            tick={{ fill: '#94a3b8', fontSize: 11 }}
            tickLine={{ stroke: '#475569' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="ovr"
            stroke={ATTRIBUTE_COLORS.ovr}
            strokeWidth={3}
            dot={{ fill: ATTRIBUTE_COLORS.ovr, r: 4 }}
            name="Overall"
          />
          {showAttributes && (
            <>
              <Line type="monotone" dataKey="spd" stroke={ATTRIBUTE_COLORS.spd} strokeWidth={1.5} dot={false} name="Speed" />
              <Line type="monotone" dataKey="sht" stroke={ATTRIBUTE_COLORS.sht} strokeWidth={1.5} dot={false} name="Shooting" />
              <Line type="monotone" dataKey="pas" stroke={ATTRIBUTE_COLORS.pas} strokeWidth={1.5} dot={false} name="Passing" />
              <Line type="monotone" dataKey="drb" stroke={ATTRIBUTE_COLORS.drb} strokeWidth={1.5} dot={false} name="Dribbling" />
              <Line type="monotone" dataKey="def" stroke={ATTRIBUTE_COLORS.def} strokeWidth={1.5} dot={false} name="Defending" />
              <Line type="monotone" dataKey="phy" stroke={ATTRIBUTE_COLORS.phy} strokeWidth={1.5} dot={false} name="Physicality" />
            </>
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
