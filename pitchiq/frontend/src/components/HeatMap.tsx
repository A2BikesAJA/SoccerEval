import { cn } from '../lib/utils';

interface HeatMapProps {
  positions: { x: number; y: number; intensity?: number }[];
  unobservedZones?: { x: number; y: number; w: number; h: number }[];
  playerName?: string;
  className?: string;
}

const PITCH_WIDTH = 600;
const PITCH_HEIGHT = 400;
const PITCH_PADDING = 20;

export default function HeatMap({
  positions,
  unobservedZones = [],
  playerName,
  className,
}: HeatMapProps) {
  // Generate heatmap cells from positions
  const gridCols = 20;
  const gridRows = 14;
  const cellWidth = PITCH_WIDTH / gridCols;
  const cellHeight = PITCH_HEIGHT / gridRows;

  // Count positions in each cell
  const heatGrid: number[][] = Array.from({ length: gridRows }, () =>
    Array(gridCols).fill(0)
  );

  positions.forEach(({ x, y }) => {
    const col = Math.min(gridCols - 1, Math.max(0, Math.floor(x * gridCols)));
    const row = Math.min(gridRows - 1, Math.max(0, Math.floor(y * gridRows)));
    heatGrid[row][col]++;
  });

  const maxCount = Math.max(1, ...heatGrid.flat());

  return (
    <div className={cn('relative inline-block', className)}>
      {playerName && (
        <div className="text-sm font-medium text-slate-300 mb-2">{playerName} — Position Heatmap</div>
      )}
      <svg
        viewBox={`0 0 ${PITCH_WIDTH + PITCH_PADDING * 2} ${PITCH_HEIGHT + PITCH_PADDING * 2}`}
        className="w-full max-w-2xl"
      >
        {/* Pitch background */}
        <rect
          x={PITCH_PADDING}
          y={PITCH_PADDING}
          width={PITCH_WIDTH}
          height={PITCH_HEIGHT}
          fill="#1a472a"
          rx={4}
        />

        {/* Pitch lines */}
        <g stroke="#2d6b3f" strokeWidth={1.5} fill="none">
          {/* Outline */}
          <rect x={PITCH_PADDING} y={PITCH_PADDING} width={PITCH_WIDTH} height={PITCH_HEIGHT} />
          {/* Center line */}
          <line
            x1={PITCH_PADDING + PITCH_WIDTH / 2}
            y1={PITCH_PADDING}
            x2={PITCH_PADDING + PITCH_WIDTH / 2}
            y2={PITCH_PADDING + PITCH_HEIGHT}
          />
          {/* Center circle */}
          <circle
            cx={PITCH_PADDING + PITCH_WIDTH / 2}
            cy={PITCH_PADDING + PITCH_HEIGHT / 2}
            r={45}
          />
          {/* Left penalty area */}
          <rect x={PITCH_PADDING} y={PITCH_PADDING + 90} width={80} height={220} />
          {/* Right penalty area */}
          <rect x={PITCH_PADDING + PITCH_WIDTH - 80} y={PITCH_PADDING + 90} width={80} height={220} />
          {/* Left goal area */}
          <rect x={PITCH_PADDING} y={PITCH_PADDING + 140} width={30} height={120} />
          {/* Right goal area */}
          <rect x={PITCH_PADDING + PITCH_WIDTH - 30} y={PITCH_PADDING + 140} width={30} height={120} />
        </g>

        {/* Heatmap cells */}
        {heatGrid.map((row, ri) =>
          row.map((count, ci) => {
            if (count === 0) return null;
            const intensity = count / maxCount;
            return (
              <rect
                key={`${ri}-${ci}`}
                x={PITCH_PADDING + ci * cellWidth}
                y={PITCH_PADDING + ri * cellHeight}
                width={cellWidth}
                height={cellHeight}
                fill={`rgba(239, 68, 68, ${intensity * 0.7})`}
                rx={2}
              />
            );
          })
        )}

        {/* Unobserved zones (grayed out) */}
        {unobservedZones.map((zone, i) => (
          <rect
            key={`unobs-${i}`}
            x={PITCH_PADDING + zone.x * PITCH_WIDTH}
            y={PITCH_PADDING + zone.y * PITCH_HEIGHT}
            width={zone.w * PITCH_WIDTH}
            height={zone.h * PITCH_HEIGHT}
            fill="rgba(100, 116, 139, 0.4)"
            stroke="rgba(100, 116, 139, 0.6)"
            strokeWidth={0.5}
            strokeDasharray="4 2"
          />
        ))}
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-red-500/20" />
          <span>Low</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-red-500/50" />
          <span>Medium</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-red-500/80" />
          <span>High</span>
        </div>
        {unobservedZones.length > 0 && (
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-sm bg-slate-500/40 border border-dashed border-slate-500/60" />
            <span>Unobserved</span>
          </div>
        )}
      </div>
    </div>
  );
}
