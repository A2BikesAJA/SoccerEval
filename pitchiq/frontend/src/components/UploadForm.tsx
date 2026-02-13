import { useState, useRef, type ChangeEvent, type FormEvent } from 'react';
import { cn } from '../lib/utils';

interface RosterEntry {
  jersey_number: number;
  name: string;
  position: string;
}

interface UploadFormProps {
  teams: { id: number; name: string }[];
  onSubmit: (formData: FormData) => Promise<void>;
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

const COMPETITION_TIERS = [
  { value: 1, label: 'Tier 1 — Elite (MLS NEXT / ECNL)' },
  { value: 2, label: 'Tier 2 — National (GA / MLS NEXT non-MLS)' },
  { value: 3, label: 'Tier 3 — High National (ECRL / DPL)' },
  { value: 4, label: 'Tier 4 — National/Regional (NPL / USYS NL)' },
  { value: 5, label: 'Tier 5 — State Premier' },
  { value: 6, label: 'Tier 6 — Competitive Travel' },
  { value: 7, label: 'Tier 7 — Recreational+' },
  { value: 8, label: 'Tier 8 — Recreational' },
];

const AGE_GROUPS = ['U8', 'U9', 'U10', 'U11', 'U12', 'U13', 'U14', 'U15', 'U16', 'U17', 'U18', 'U19'];

const FORMATIONS = [
  '4-3-3', '4-4-2', '4-2-3-1', '3-5-2', '3-4-3',
  '4-1-4-1', '4-3-1-2', '5-3-2', '4-5-1', '3-3-4',
];

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
  const [cameraSource, setCameraSource] = useState('veo_followcam');
  const [roster, setRoster] = useState<RosterEntry[]>([
    { jersey_number: 1, name: '', position: 'GK' },
  ]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedCamera = CAMERA_SOURCES.find((c) => c.value === cameraSource);

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) setFile(e.target.files[0]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) setFile(e.dataTransfer.files[0]);
  };

  const addRosterEntry = () => {
    const nextNum = roster.length > 0 ? Math.max(...roster.map((r) => r.jersey_number)) + 1 : 1;
    setRoster([...roster, { jersey_number: nextNum, name: '', position: '' }]);
  };

  const removeRosterEntry = (idx: number) => {
    setRoster(roster.filter((_, i) => i !== idx));
  };

  const updateRoster = (idx: number, field: keyof RosterEntry, value: string | number) => {
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
    formData.append('camera_source_type', cameraSource);

    const validRoster = roster.filter((r) => r.name.trim());
    if (validRoster.length > 0) {
      formData.append('roster_json', JSON.stringify(validRoster));
    }

    try {
      await onSubmit(formData);
    } finally {
      setUploading(false);
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
          <label className="text-sm font-medium text-slate-300">Roster</label>
          <button
            type="button"
            onClick={addRosterEntry}
            className="text-xs text-emerald-400 hover:text-emerald-300"
          >
            + Add Player
          </button>
        </div>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {roster.map((entry, idx) => (
            <div key={idx} className="flex gap-2 items-center">
              <input
                type="number"
                value={entry.jersey_number}
                onChange={(e) => updateRoster(idx, 'jersey_number', parseInt(e.target.value) || 0)}
                className="w-16 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1.5 text-white text-center text-sm"
                placeholder="#"
              />
              <input
                type="text"
                value={entry.name}
                onChange={(e) => updateRoster(idx, 'name', e.target.value)}
                className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-white text-sm placeholder-slate-500"
                placeholder="Player name"
              />
              <select
                value={entry.position}
                onChange={(e) => updateRoster(idx, 'position', e.target.value)}
                className="w-20 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1.5 text-white text-sm"
              >
                <option value="">Pos</option>
                <option value="GK">GK</option>
                <option value="CB">CB</option>
                <option value="LB">LB</option>
                <option value="RB">RB</option>
                <option value="CDM">CDM</option>
                <option value="CM">CM</option>
                <option value="CAM">CAM</option>
                <option value="LW">LW</option>
                <option value="RW">RW</option>
                <option value="ST">ST</option>
              </select>
              <button
                type="button"
                onClick={() => removeRosterEntry(idx)}
                className="text-slate-500 hover:text-red-400 text-sm px-1"
              >
                ×
              </button>
            </div>
          ))}
        </div>
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
