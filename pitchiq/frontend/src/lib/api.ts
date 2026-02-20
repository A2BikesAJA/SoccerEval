import axios from 'axios';

// In Docker: VITE_API_URL is set to http://localhost:8000/api/v1
// (browser calls backend directly via port mapping, no proxy needed)
// Local dev: falls back to /api/v1 (uses Vite proxy)
const baseURL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Clubs
export const clubsApi = {
  list: () => api.get('/clubs/'),
  create: (data: { name: string; logo_url?: string }) => api.post('/clubs/', data),
  get: (id: number) => api.get(`/clubs/${id}`),
};

// Teams
export const teamsApi = {
  list: (clubId?: number) => api.get('/teams/', { params: { club_id: clubId } }),
  create: (data: any) => api.post('/teams/', data),
  get: (id: number) => api.get(`/teams/${id}`),
  update: (id: number, data: any) => api.put(`/teams/${id}`, data),
};

// Players
export const playersApi = {
  list: (teamId?: number) => api.get('/players/', { params: { team_id: teamId } }),
  create: (data: any) => api.post('/players/', data),
  get: (id: number) => api.get(`/players/${id}`),
  importRoster: (teamId: number, roster: any[]) => api.post(`/players/roster/${teamId}`, roster),
};

// Games
export const gamesApi = {
  list: (teamId?: number) => api.get('/games/', { params: { team_id: teamId } }),
  get: (id: number) => api.get(`/games/${id}`),
  upload: (formData: FormData, onProgress?: (pct: number) => void) => api.post('/games/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      const pct = progressEvent.total ? Math.round((progressEvent.loaded * 100) / progressEvent.total) : 0;
      onProgress?.(pct);
    },
  }),
};

// Stats
export const statsApi = {
  getTeamStats: (gameId: number) => api.get(`/stats/game/${gameId}/team`),
  getPlayerStats: (gameId: number) => api.get(`/stats/game/${gameId}/players`),
  getPlayerHistory: (playerId: number) => api.get(`/stats/player/${playerId}/history`),
};

// PIQ
export const piqApi = {
  getPlayerRating: (playerId: number) => api.get(`/piq/player/${playerId}`),
  getPlayerHistory: (playerId: number) => api.get(`/piq/player/${playerId}/history`),
  scouting: (params: any) => api.get('/piq/scouting', { params }),
  whatIf: (playerId: number, targetTier: number) => api.get(`/piq/what-if/${playerId}`, { params: { target_tier: targetTier } }),
  compare: (playerIds: number[]) => api.get('/piq/compare', { params: { player_ids: playerIds.join(',') } }),
};

// Processing
export const processingApi = {
  getStatus: (gameId: number) => api.get(`/processing/game/${gameId}`),
  retry: (gameId: number) => api.post(`/processing/game/${gameId}/retry`),
};

export default api;
