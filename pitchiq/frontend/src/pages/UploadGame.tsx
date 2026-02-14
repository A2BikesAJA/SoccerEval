import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import UploadForm from '../components/UploadForm';

// Demo teams
const DEMO_TEAMS = [
  { id: 1, name: 'FC Warriors U14 Boys' },
  { id: 2, name: 'FC Warriors U12 Girls' },
];

export default function UploadGame() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (formData: FormData) => {
    setError(null);
    try {
      const response = await fetch('/api/v1/games/upload', {
        method: 'POST',
        body: formData,
      });
      const text = await response.text();
      if (!response.ok) {
        let detail = 'Upload failed';
        try {
          const data = JSON.parse(text);
          detail = data.detail || detail;
        } catch {
          detail = text || `Server error (${response.status})`;
        }
        throw new Error(detail);
      }
      const game = JSON.parse(text);
      navigate(`/game/${game.id}`);
    } catch (err: any) {
      setError(err.message || 'Upload failed. Please try again.');
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Upload Game</h1>
        <p className="text-sm text-slate-400 mt-1">
          Upload game footage to receive AI-powered player analytics and ratings.
        </p>
      </div>

      {/* Camera Tips Panel */}
      <div className="mb-6 p-4 bg-blue-900/10 border border-blue-800/20 rounded-xl">
        <h3 className="text-sm font-medium text-blue-300 mb-2">Camera Tips for Best Results</h3>
        <ul className="text-xs text-blue-300/70 space-y-1">
          <li>• For VEO Follow Cam footage, adding a sideline parent video improves off-ball player tracking significantly.</li>
          <li>• If your club has VEO API access, the panoramic view dramatically improves tracking accuracy.</li>
          <li>• Position any secondary camera on the opposite side from the VEO for maximum field coverage.</li>
          <li>• Static elevated cameras (press box, HiPod) provide the best single-source tracking quality.</li>
        </ul>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-800/30 rounded-lg">
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      <UploadForm teams={DEMO_TEAMS} onSubmit={handleSubmit} />
    </div>
  );
}
