import { cn } from '../lib/utils';

interface ProcessingStatusProps {
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  progressPct: number;
  currentStage?: string;
  errorMessage?: string;
}

const STAGES = [
  'Transcoding video',
  'Extracting frames',
  'Detecting players & ball',
  'Classifying teams',
  'Reading jersey numbers',
  'Tracking players',
  'Computing statistics',
  'Calculating scores',
  'Updating PIQ ratings',
  'Finalizing',
];

export default function ProcessingStatus({
  status,
  progressPct,
  currentStage,
  errorMessage,
}: ProcessingStatusProps) {
  const isRunning = status === 'running';
  const isComplete = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <div className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-white">Processing Status</h3>
        <span className={cn(
          'text-xs px-2.5 py-1 rounded-full font-medium',
          isComplete ? 'bg-emerald-900/50 text-emerald-400' :
          isFailed ? 'bg-red-900/50 text-red-400' :
          isRunning ? 'bg-blue-900/50 text-blue-400' :
          'bg-slate-700 text-slate-400',
        )}>
          {status === 'queued' ? 'Queued' :
           status === 'running' ? 'Processing' :
           status === 'completed' ? 'Complete' :
           status === 'failed' ? 'Error' : 'Cancelled'}
        </span>
      </div>

      {/* Progress bar */}
      <div className="h-3 bg-slate-700 rounded-full overflow-hidden mb-2">
        <div
          className={cn(
            'h-full rounded-full transition-all duration-500',
            isComplete ? 'bg-emerald-500' :
            isFailed ? 'bg-red-500' :
            'bg-gradient-to-r from-blue-500 to-cyan-400',
            isRunning && 'animate-pulse',
          )}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <div className="flex justify-between text-xs">
        <span className="text-slate-400">
          {currentStage || (isComplete ? 'Processing complete' : 'Waiting...')}
        </span>
        <span className="text-slate-400 font-mono">{progressPct.toFixed(0)}%</span>
      </div>

      {/* Stage indicators */}
      {isRunning && (
        <div className="mt-4 space-y-1.5">
          {STAGES.map((stage, i) => {
            const stageProgress = (i / STAGES.length) * 100;
            const isDone = progressPct > stageProgress + (100 / STAGES.length);
            const isCurrent = currentStage?.toLowerCase().includes(stage.toLowerCase().split(' ')[0]);
            return (
              <div key={stage} className="flex items-center gap-2 text-xs">
                <div className={cn(
                  'w-2 h-2 rounded-full flex-shrink-0',
                  isDone ? 'bg-emerald-400' :
                  isCurrent ? 'bg-blue-400 animate-pulse' :
                  'bg-slate-600',
                )} />
                <span className={cn(
                  isDone ? 'text-slate-400' :
                  isCurrent ? 'text-white font-medium' :
                  'text-slate-600',
                )}>
                  {stage}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Error */}
      {isFailed && errorMessage && (
        <div className="mt-3 p-3 bg-red-900/20 border border-red-800/30 rounded-lg">
          <p className="text-xs text-red-400">{errorMessage}</p>
        </div>
      )}
    </div>
  );
}
