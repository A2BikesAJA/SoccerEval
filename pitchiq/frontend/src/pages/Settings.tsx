import { useState } from 'react';
import CompetitionTierSelector from '../components/CompetitionTierSelector';

export default function Settings() {
  const [clubName, setClubName] = useState('FC Warriors');
  const [teamName, setTeamName] = useState('U14 Boys');
  const [tier, setTier] = useState(1);
  const [ageGroup, setAgeGroup] = useState('U14');
  const [leagueName, setLeagueName] = useState('ECNL');
  const [defaultCamera, setDefaultCamera] = useState('veo_followcam');
  const [piqMinGames, setPiqMinGames] = useState(3);
  const [detectionFps, setDetectionFps] = useState(2.0);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Manage your club, team, and processing preferences</p>
      </div>

      <div className="space-y-8">
        {/* Club Profile */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Club Profile</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Club Name</label>
              <input
                type="text"
                value={clubName}
                onChange={(e) => setClubName(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Team Name</label>
              <input
                type="text"
                value={teamName}
                onChange={(e) => setTeamName(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Age Group</label>
                <select
                  value={ageGroup}
                  onChange={(e) => setAgeGroup(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
                >
                  {['U8','U9','U10','U11','U12','U13','U14','U15','U16','U17','U18','U19'].map((ag) => (
                    <option key={ag} value={ag}>{ag}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-slate-400 mb-1">League Name</label>
                <input
                  type="text"
                  value={leagueName}
                  onChange={(e) => setLeagueName(e.target.value)}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
                />
              </div>
            </div>
          </div>
        </section>

        {/* Competition Tier */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Competition Tier</h2>
          <CompetitionTierSelector value={tier} onChange={setTier} />
        </section>

        {/* PIQ Rating Preferences */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">PIQ Rating Preferences</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Minimum games for PIQ Rating display
              </label>
              <select
                value={piqMinGames}
                onChange={(e) => setPiqMinGames(Number(e.target.value))}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              >
                {[2, 3, 4, 5].map((n) => (
                  <option key={n} value={n}>{n} games</option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">
                Players with fewer games will show "Calculating..." instead of a rating.
              </p>
            </div>
          </div>
        </section>

        {/* Processing Preferences */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Processing Preferences</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Default Camera Platform</label>
              <select
                value={defaultCamera}
                onChange={(e) => setDefaultCamera(e.target.value)}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value="veo_followcam">VEO Follow Cam</option>
                <option value="veo_panoramic">VEO Panoramic</option>
                <option value="trace">Trace</option>
                <option value="pixellot">Pixellot</option>
                <option value="sideline">Sideline Camera</option>
                <option value="static_elevated">Static Elevated</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">
                Detection Frame Rate (fps)
              </label>
              <select
                value={detectionFps}
                onChange={(e) => setDetectionFps(Number(e.target.value))}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm"
              >
                <option value={0.5}>0.5 fps (faster processing, lower accuracy)</option>
                <option value={1.0}>1.0 fps (balanced)</option>
                <option value={2.0}>2.0 fps (recommended)</option>
                <option value={4.0}>4.0 fps (higher accuracy, slower)</option>
              </select>
            </div>
          </div>
        </section>

        {/* Export */}
        <section className="bg-slate-800/50 rounded-xl border border-white/10 p-5">
          <h2 className="text-sm font-bold text-white mb-4">Data Export</h2>
          <div className="flex gap-3">
            <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors">
              Export All Stats (CSV)
            </button>
            <button className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm text-white transition-colors">
              Export PIQ Ratings (CSV)
            </button>
          </div>
        </section>

        {/* Save */}
        <button
          onClick={handleSave}
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-500 rounded-xl font-semibold text-white transition-colors"
        >
          {saved ? 'Saved!' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}
