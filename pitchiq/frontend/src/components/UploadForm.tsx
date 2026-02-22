import { useState, useEffect, useRef, type ChangeEvent, type FormEvent } from 'react';
import { cn } from '../lib/utils';
import { playersApi } from '../lib/api';

interface PlayerFromAPI {
  id: number;
  jersey_number: number | null;
  name: string;
  position: string | null;
}

interface RosterEntry {
  player_id: number | null;
  jersey_number: number;
  name: string;
  position: string;
  selected: boolean;
}

interface UploadFormProps {
  teams: { id: number; name: string; default_formation?: string | null }[];
  onSubmit: (formData: FormData, onProgress: (pct: number) => void) => Promise<void>;
}

const CAMERA_SOURCES = [
  { value: 'veo_followcam', label: 'VEO Follow Cam', tip: 'Most common. ~45% field coverage.' },
  { value: 'veo_panoramic', label: 'VEO Panoramic', tip: 'Full field view if available.' },
  { value: 'trace', label: 'Trace', tip: 'Similar to VEO Follow Cam.' },
  { value: 'pixellot', label: 'Pixellot / Pixio', tip: 'AI auto-tracking camera.' },
  { value: 'sideline', label: 'Sideline Camera', tip: 'Parent or coach filmed.' },
  { value: 'static_elevated', label: 'Static Elevated', tip: 'Best case — wide field view.' },
  { value: 'other', label: 'Other', tip: 'Unknown camera type.' },
];

const MATCH_FORMATS = [
  { value: '5v5', label: '5 v 5', players: 5 },
  { value: '7v7', label: '7 v 7', players: 7 },
  { value: '9v9', label: '9 v 9', players: 9 },
  { value: '11v11', label: '11 v 11', players: 11 },
];

const AGE_GROUPS = ['U8', 'U9', 'U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16', 'U17', 'U18', 'U19'];

const FORMATIONS = [
  '4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '3-4-3',
  '4-1-4-1', '4-3-1-2', '5-3-2', '4-5-1', '3-3-4',
];

const POSITIONS = ['GK', 'CB', 'LB', 'RB', 'CDM', 'CM', 'CAM', 'LW', 'RW', 'ST'];

export default function UploadForm({ teams, onSubmit }: UploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [teamId, setTeamId] = useState<number>(teams[0]?.id || 0);
  const [opponent, setOpponent] = useState('');
  const [gameDate, setGameDate] = useState('');
  const [ageGroup, setAgeGroup] = useState('U12');
  const [formation, setFormation] = useState('4-3-3');
  const [matchFormat, setMatchFormat] = useState('11v11');
  const [cameraSource, setCameraSource] = useState('veo_followcam');
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [loadingRoster, setLoadingRoster] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedCamera = CAMERA_SOURCES.find((c) => c.value === cameraSource);
  const selectedFormat = MATCH_FORMATS.find((f) => f.value === matchFormat);
  const selectedCount = roster.filter((r) => r.selected).length;
  const expectedPlayers = selectedFormat?.players || 11;

  // Auto-load roster and default formation when team changes
  useEffect(() => {
    if (!teamId) return;
    const team = teams.find((t) => t.id === teamId);
    if (team?.default_formation) {
      setFormation(team.default_formation);
    }
    setLoadingRoster(true);
    playersApi.list(teamId)
      .then((res) => {
        const players: PlayerFromAPI[] = res.data;
        if (players.length > 0) {
          setRoster(
            players.map((p) => ({
              player_id: p.id,
              jersey_number: p.jersey_number ?? 0,
              name: p.name,
              position: p.position ?? '',
              selected: true,
            }))
          );
        } else {
          setRoster([]);
        }
      })
      .catch(() => setRoster([]))
      .finally(() => setLoadingRoster(false));
  }, [teamId]);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
  };

  const togglePlayer = (idx: number) => {
    const updated = [...roster];
    updated[idx].selected = !updated[idx].selected;
    setRoster(updated);
  };

  const selectAll = () => setRoster(roster.map((r) => ({ ...r, selected: true })));
  const selectNone = () => setRoster(roster.map((r) => ({ ...r, selected: false })));

  const addManualEntry = () => {
    const nextNum = roster.length > 0 ? Math.max(...roster.map((r) => r.jersey_number)) + 1 : 1;
    setRoster([...roster, { player_id: null, jersey_number: nextNum, name: '', position: '', selected: true }]);
  };

  const removeEntry = (idx: number) => {
    setRoster(roster.filter((_, i) => i !== idx));
  };

  const updateEntry = (idx: number, field: keyof RosterEntry, value: string | number | boolean) => {
    const updated = [...roster];
    (updated[idx] as any)[field] = value;
    setRoster(updated);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file || !opponent || !gameDate) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('video', file);
    formData.append('team_id', String(teamId));
    formData.append('opponent_name', opponent);
    formData.append('game_date', gameDate);
    formData.append('age_group', ageGroup);
    formData.append('formation', formation);
    formData.append('match_format', matchFormat);
    formData.append('camera_source_type', cameraSource);

    const selectedRoster = roster
      .filter((r) => r.selected && r.name.trim())
      .map((r) => ({
        jersey_number: r.jersey_number,
        name: r.name,
        position: r.position,
      }));
    if (selectedRoster.length > 0) {
      formData.append('roster_json', JSON.stringify(selectedRoster));
    }

    try {
      await onSubmit(formData, (pct) => setUploadProgress(pct));
    } finally {
      setUploading(false);
      setUploadProgress(0);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-3xl">
      {/* Video Upload */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">Game Video</label>
        <div
          className={cn(
            'border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer',
            dragActive ? 'border-emerald-400 bg-emerald-400/5' : 'border-slate-600 hover:border-slate-500',
            file && 'border-emerald-500 bg-emerald-500/5',
          )}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".mp4,.mov,.avi,.mkv"
            onChange={handleFileChange}
            className="hidden"
          />
          {file ? (
            <div>
              <p className="text-emerald-400 font-medium">{file.name}</p>
              <p className="text-sm text-slate-400 mt-1">
                {(file.size / (1024 * 1024)).toFixed(0)} MB
              </p>
            </div>
          ) : (
            <div>
              <p className="text-slate-400">Drag and drop your game video here</p>
              <p className="text-sm text-slate-500 mt-1">MP4, MOV, AVI, MKV — up to 5GB</p>
            </div>
          )}
        </div>
      </div>

      {/* Camera Source */}
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">Camera Source</label>
        <select
          value={cameraSource}
          onChange={(e) => setCameraSource(e.target.value)}
          className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white"
        >
          {CAMERA_SOURCES.map((src) => (
            <option key={src.value} value={src.value}>{src.label}</option>
          ))}
        </select>
        {selectedCamera && (
          <div className="mt-2 p-3 bg-blue-900/20 border border-blue-800/30 rounded-lg">
            <p className="text-xs text-blue-300">{selectedCamera.tip}</p>
            {cameraSource === 'veo_followcam' && (
              <p className="text-xs text-blue-400 mt-1">
                Tip: For best results, also upload a sideline parent video as a secondary source.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Game Details */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Team</label>
          <select
            value={teamId}
            onChange={(e) => setTeamId(Number(e.target.value))}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white"
          >
            {teams.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Opponent</label>
          <input
            type="text"
            value={opponent}
            onChange={(e) => setOpponent(e.target.value)}
            placeholder="Opponent team name"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white placeholder-slate-500"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Game Date</label>
          <input
            type="date"
            value={gameDate}
            onChange={(e) => setGameDate(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Match Format</label>
          <div className="flex gap-2">
            {MATCH_FORMATS.map((fmt) => (
              <button
                key={fmt.value}
                type="button"
                onClick={() => setMatchFormat(fmt.value)}
                className={cn(
                  'flex-1 py-2 rounded-lg text-sm font-medium transition-colors border',
                  matchFormat === fmt.value
                    ? 'bg-emerald-600 border-emerald-500 text-white'
                    : 'bg-slate-800 border-slate-600 text-slate-400 hover:border-slate-500',
                )}
              >
                {fmt.label}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Age Group</label>
          <select
            value={ageGroup}
            onChange={(e) => setAgeGroup(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white"
          >
            {AGE_GROUPS.map((ag) => (
              <option key={ag} value={ag}>{ag}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">Formation</label>
          <select
            value={formation}
            onChange={(e) => setFormation(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white"
          >
            {FORMATIONS.map((f) => (
              <option key={f} value={f}>{f}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Roster */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <label className="text-sm font-medium text-slate-300">Game Day Roster</label>
            <span className={cn(
              'text-xs px-2 py-0.5 rounded-full',
              selectedCount === expectedPlayers
                ? 'bg-emerald-900/30 text-emerald-400'
                : selectedCount > expectedPlayers
                  ? 'bg-amber-900/30 text-amber-400'
                  : 'bg-slate-700 text-slate-400',
            )}>
              {selectedCount} / {expectedPlayers} selected
            </span>
          </div>
          <div className="flex items-center gap-3">
            <button type="button" onClick={selectAll} className="text-xs text-slate-400 hover:text-slate-300">
              Select all
            </button>
            <button type="button" onClick={selectNone} className="text-xs text-slate-400 hover:text-slate-300">
              Clear
            </button>
            <button type="button" onClick={addManualEntry} className="text-xs text-emerald-400 hover:text-emerald-300">
              + Add Player
            </button>
          </div>
        </div>

        {loadingRoster ? (
          <div className="text-center py-6 text-slate-500 text-sm">Loading team roster...</div>
        ) : roster.length === 0 ? (
          <div className="text-center py-6">
            <p className="text-slate-500 text-sm mb-2">No players on this team yet.</p>
            <p className="text-slate-600 text-xs">Add players in Settings, or use "+ Add Player" above for a one-off entry.</p>
          </div>
        ) : (
          <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
            {roster.map((entry, idx) => (
              <div
                key={idx}
                className={cn(
                  'flex gap-2 items-center px-3 py-2 rounded-lg border transition-colors',
                  entry.selected
                    ? 'bg-slate-800/60 border-slate-600'
                    : 'bg-slate-900/40 border-slate-700/50 opacity-50',
                )}
              >
                <input
                  type="checkbox"
                  checked={entry.selected}
                  onChange={() => togglePlayer(idx)}
                  className="w-4 h-4 rounded border-slate-500 text-emerald-500 focus:ring-emerald-500 bg-slate-700"
                />
                <input
                  type="number"
                  value={entry.jersey_number}
                  onChange={(e) => updateEntry(idx, 'jersey_number', parseInt(e.target.value) || 0)}
                  className="w-14 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-white text-center text-sm"
                  placeholder="#"
                />
                {entry.player_id ? (
                  <span className="flex-1 text-sm text-white truncate">{entry.name}</span>
                ) : (
                  <input
                    type="text"
                    value={entry.name}
                    onChange={(e) => updateEntry(idx, 'name', e.target.value)}
                    className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-3 py-1 text-white text-sm placeholder-slate-500"
                    placeholder="Player name"
                  />
                )}
                <select
                  value={entry.position}
                  onChange={(e) => updateEntry(idx, 'position', e.target.value)}
                  className="w-20 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1 text-white text-sm"
                >
                  <option value="">Pos</option>
                  {POSITIONS.map((pos) => (
                    <option key={pos} value={pos}>{pos}</option>
                  ))}
                </select>
                {!entry.player_id && (
                  <button
                    type="button"
                    onClick={() => removeEntry(idx)}
                    className="text-slate-500 hover:text-red-400 text-sm px-1"
                  >
                    x
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={!file || !opponent || !gameDate || uploading}
        className={cn(
          'w-full py-3 rounded-xl font-semibold text-white transition-all',
          uploading
            ? 'bg-slate-700 cursor-wait'
            : 'bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:cursor-not-allowed',
        )}
      >
        {uploading ? (
          <span>Uploading... {uploadProgress}%</span>
        ) : (
          'Upload & Process Game'
        )}
      </button>
    </form>
  );
}
