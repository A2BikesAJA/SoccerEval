// ── Enums (as const objects for erasableSyntaxOnly compatibility) ──────────

export const GameStatus = {
  PENDING: 'pending',
  UPLOADING: 'uploading',
  TRANSCODING: 'transcoding',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  ERROR: 'error',
} as const;
export type GameStatus = (typeof GameStatus)[keyof typeof GameStatus];

export const CameraSourceType = {
  VEO_FOLLOWCAM: 'veo_followcam',
  VEO_PANORAMIC: 'veo_panoramic',
  TRACE: 'trace',
  PIXELLOT: 'pixellot',
  SIDELINE: 'sideline',
  STATIC_ELEVATED: 'static_elevated',
  OTHER: 'other',
} as const;
export type CameraSourceType = (typeof CameraSourceType)[keyof typeof CameraSourceType];

export const PlayerPosition = {
  // Goalkeeper
  GK: 'GK',
  // Center Back
  CB: 'CB',
  SW: 'SW',
  // Fullback / Wingback
  LB: 'LB',
  RB: 'RB',
  LWB: 'LWB',
  RWB: 'RWB',
  // Defensive Midfielder
  CDM: 'CDM',
  DM: 'DM',
  // Central Midfielder
  CM: 'CM',
  LCM: 'LCM',
  RCM: 'RCM',
  // Attacking Midfielder
  CAM: 'CAM',
  AM: 'AM',
  // Winger
  LW: 'LW',
  RW: 'RW',
  LM: 'LM',
  RM: 'RM',
  // Striker / Forward
  ST: 'ST',
  CF: 'CF',
  LF: 'LF',
  RF: 'RF',
} as const;
export type PlayerPosition = (typeof PlayerPosition)[keyof typeof PlayerPosition];

export const AgeGroup = {
  U8: 'U8',
  U9: 'U9',
  U10: 'U10',
  U11: 'U11',
  U12: 'U12',
  U13: 'U13',
  U14: 'U14',
  U15: 'U15',
  U16: 'U16',
  U17: 'U17',
  U18: 'U18',
  U19: 'U19',
} as const;
export type AgeGroup = (typeof AgeGroup)[keyof typeof AgeGroup];

export const CompetitionTier = {
  TIER_1: 1, // MLS NEXT / ECNL
  TIER_2: 2, // MLS NEXT (non-MLS) / GA
  TIER_3: 3, // ECRL / GA Aspire / DPL
  TIER_4: 4, // NPL / USYS NL
  TIER_5: 5, // State Premier
  TIER_6: 6, // Competitive Travel
  TIER_7: 7, // Recreational+
  TIER_8: 8, // Recreational
} as const;
export type CompetitionTier = (typeof CompetitionTier)[keyof typeof CompetitionTier];

export const CompetitionTierLabels: Record<CompetitionTier, string> = {
  [CompetitionTier.TIER_1]: 'MLS NEXT / ECNL',
  [CompetitionTier.TIER_2]: 'MLS NEXT (non-MLS) / GA',
  [CompetitionTier.TIER_3]: 'ECRL / GA Aspire / DPL',
  [CompetitionTier.TIER_4]: 'NPL / USYS NL',
  [CompetitionTier.TIER_5]: 'State Premier',
  [CompetitionTier.TIER_6]: 'Competitive Travel',
  [CompetitionTier.TIER_7]: 'Recreational+',
  [CompetitionTier.TIER_8]: 'Recreational',
};

export const PIQConfidenceLevel = {
  CALCULATING: 'calculating',   // < 3 games
  PRELIMINARY: 'preliminary',   // 3-5 games
  DEVELOPING: 'developing',     // 6-10 games
  ESTABLISHED: 'established',   // 11+ games
} as const;
export type PIQConfidenceLevel = (typeof PIQConfidenceLevel)[keyof typeof PIQConfidenceLevel];

export const ProcessingJobStatus = {
  QUEUED: 'queued',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
} as const;
export type ProcessingJobStatus = (typeof ProcessingJobStatus)[keyof typeof ProcessingJobStatus];

// ── Core Data Models ───────────────────────────────────────────────────────

export interface Club {
  id: number;
  name: string;
  logo_url?: string | null;
  teams?: Team[];
}

export interface Team {
  id: number;
  club_id: number;
  name: string;
  age_group: AgeGroup;
  season?: string | null;
  competition_tier: number;
  league_name?: string | null;
  club?: Club;
  players?: Player[];
  games?: Game[];
}

export interface Player {
  id: number;
  team_id: number;
  name: string;
  jersey_number?: number | null;
  position?: PlayerPosition | null;
  photo_url?: string | null;
  team?: Team;
  game_appearances?: GamePlayer[];
  piq_ratings?: PIQRating[];
}

export interface Game {
  id: number;
  team_id: number;
  opponent_name: string;
  game_date: string; // ISO date string
  age_group?: string | null;
  formation?: string | null;
  video_path?: string | null;
  status: GameStatus;
  score_home?: number | null;
  score_away?: number | null;
  duration_minutes?: number | null;
  team?: Team;
  video_sources?: GameVideoSource[];
  game_players?: GamePlayer[];
  processing_jobs?: ProcessingJob[];
}

export interface GameVideoSource {
  id: number;
  game_id: number;
  source_type: CameraSourceType;
  video_path: string;
  is_primary: boolean;
  resolution?: string | null;
  fps?: number | null;
  temporal_offset_ms: number;
  field_coverage_pct?: number | null;
}

export interface GamePlayer {
  id: number;
  game_id: number;
  player_id: number;
  position_played?: string | null;
  minutes_played: number;
  started: boolean;
  screen_time_ratio: number;
  adjusted_screen_time_ratio: number;
  visible_frame_count: number;
  total_game_frames: number;
  identity_confidence: number;
  player?: Player;
  game?: Game;
  stats?: PlayerGameStats[];
  score?: PlayerScore | null;
}

// ── Stats Models ───────────────────────────────────────────────────────────

export interface PlayerGameStats {
  id: number;
  game_player_id: number;
  metric_name: string;
  metric_value: number;
  data_density: number;
  is_extrapolated: boolean;
}

export interface TeamGameStats {
  id: number;
  game_id: number;
  metric_name: string;
  metric_value: number;
}

// ── Score & PIQ Models ─────────────────────────────────────────────────────

export interface PlayerScore {
  id: number;
  game_player_id: number;
  overall_score: number;
  confidence: number;
  category_scores?: Record<string, number> | null;
  bonus_events?: Record<string, any>[] | null;
  raw_composite?: number | null;
  minutes_adjustment: number;
}

export interface PIQSubAttributes {
  // Speed sub-attributes
  sprint_speed?: number;
  acceleration?: number;
  agility?: number;
  // Shooting sub-attributes
  finishing?: number;
  shot_power?: number;
  long_shots?: number;
  volleys?: number;
  penalties?: number;
  // Passing sub-attributes
  vision?: number;
  crossing?: number;
  short_passing?: number;
  long_passing?: number;
  free_kick_accuracy?: number;
  curve?: number;
  // Dribbling sub-attributes
  ball_control?: number;
  dribbling?: number;
  composure?: number;
  // Defending sub-attributes
  marking?: number;
  standing_tackle?: number;
  sliding_tackle?: number;
  interceptions?: number;
  heading_accuracy?: number;
  // Physical sub-attributes
  stamina?: number;
  strength?: number;
  jumping?: number;
  // GK-specific sub-attributes
  gk_diving?: number;
  gk_handling?: number;
  gk_positioning?: number;
  gk_reflexes?: number;
  [key: string]: number | undefined;
}

export interface PIQRating {
  id: number;
  player_id: number;
  ovr: number;
  spd: number;
  sht: number;
  pas: number;
  drb: number;
  def: number;
  phy: number;
  sub_attributes?: PIQSubAttributes | null;
  competition_tier?: number | null;
  level_multiplier_applied?: number | null;
  games_analyzed_count: number;
  confidence_level: PIQConfidenceLevel;
  player?: Player;
  history?: PIQRatingHistory[];
}

export interface PIQRatingHistory {
  id: number;
  piq_rating_id: number;
  player_id: number;
  ovr: number;
  attributes?: Record<string, number> | null;
  games_analyzed_count: number;
  triggered_by_game_id?: number | null;
  snapshot_date: string; // ISO date string
}

// ── Tracking & Processing ──────────────────────────────────────────────────

export interface TrackingEvent {
  id: number;
  game_id: number;
  event_type: string;
  player_id?: number | null;
  timestamp_seconds: number;
  x_position?: number | null;
  y_position?: number | null;
  metadata?: Record<string, any> | null;
  source_video_id?: number | null;
}

export interface ProcessingJob {
  id: number;
  game_id: number;
  status: ProcessingJobStatus;
  progress_pct: number;
  current_stage?: string | null;
  started_at?: string | null;  // ISO datetime string
  completed_at?: string | null; // ISO datetime string
  error_message?: string | null;
}

// ── Position Group Mapping (mirrors backend POSITION_GROUP_MAP) ────────────

export const PositionGroupMap: Record<string, string> = {
  GK: 'GK',
  CB: 'CB',
  SW: 'CB',
  LB: 'FB',
  RB: 'FB',
  LWB: 'FB',
  RWB: 'FB',
  CDM: 'CDM',
  DM: 'CDM',
  CM: 'CM',
  LCM: 'CM',
  RCM: 'CM',
  CAM: 'CAM',
  AM: 'CAM',
  LW: 'W',
  RW: 'W',
  LM: 'W',
  RM: 'W',
  ST: 'ST',
  CF: 'ST',
  LF: 'ST',
  RF: 'ST',
};
