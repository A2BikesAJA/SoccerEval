import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import UploadGame from './pages/UploadGame';
import GameAnalysis from './pages/GameAnalysis';
import PlayerReport from './pages/PlayerReport';
import ScoutingView from './pages/ScoutingView';
import SeasonAnalytics from './pages/SeasonAnalytics';
import Settings from './pages/Settings';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<UploadGame />} />
          <Route path="/game/:gameId" element={<GameAnalysis />} />
          <Route path="/player/:playerId" element={<PlayerReport />} />
          <Route path="/scouting" element={<ScoutingView />} />
          <Route path="/season" element={<SeasonAnalytics />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
