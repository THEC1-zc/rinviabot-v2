-- ============================================
-- TOKEN-CCG Database Schema
-- Supabase PostgreSQL
-- Version: 1.0.0
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- USERS TABLE
-- ============================================
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  wallet_address TEXT UNIQUE,
  farcaster_fid INTEGER UNIQUE,
  username TEXT,
  avatar_url TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for wallet lookup
CREATE INDEX idx_users_wallet ON users(wallet_address);
CREATE INDEX idx_users_farcaster ON users(farcaster_fid);

-- ============================================
-- CARDS TABLE (Single minted cards)
-- ============================================
CREATE TABLE cards (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  house TEXT NOT NULL CHECK (house IN ('bitcoin', 'ethereum', 'base', 'tysm')),
  faction_name TEXT NOT NULL,
  faction_icon TEXT DEFAULT '🎴',
  value INTEGER NOT NULL CHECK (value >= 2 AND value <= 15),
  display_value TEXT NOT NULL,
  card_name TEXT,
  xp INTEGER DEFAULT 0,
  games_played INTEGER DEFAULT 0,
  wins INTEGER DEFAULT 0,
  onchain_token_id TEXT, -- Future: NFT token ID
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Unique constraint: one card per value per faction per user
  UNIQUE(user_id, faction_name, value)
);

-- Indexes
CREATE INDEX idx_cards_user ON cards(user_id);
CREATE INDEX idx_cards_house ON cards(house);
CREATE INDEX idx_cards_faction ON cards(faction_name);

-- ============================================
-- DECKS TABLE (10-card decks from Deck Minter)
-- ============================================
CREATE TABLE decks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  house TEXT NOT NULL CHECK (house IN ('bitcoin', 'ethereum', 'base', 'tysm')),
  faction_name TEXT NOT NULL,
  faction_icon TEXT DEFAULT '🎴',
  cards JSONB NOT NULL, -- Array of 10 card objects
  onchain_token_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_decks_user ON decks(user_id);
CREATE INDEX idx_decks_house ON decks(house);

-- ============================================
-- BATTLE_DECKS TABLE (2 decks combined)
-- ============================================
CREATE TABLE battle_decks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  deck1_house TEXT NOT NULL,
  deck2_house TEXT NOT NULL,
  deck1_cards JSONB NOT NULL, -- Array of card UIDs
  deck2_cards JSONB NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  
  -- Decks must be different houses
  CHECK (deck1_house != deck2_house)
);

-- Index
CREATE INDEX idx_battle_decks_user ON battle_decks(user_id);

-- ============================================
-- GAMES TABLE (Match history)
-- ============================================
CREATE TABLE games (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  player1_id UUID REFERENCES users(id),
  player2_id UUID REFERENCES users(id), -- NULL for AI games
  player1_battle_deck_id UUID REFERENCES battle_decks(id),
  player2_battle_deck_id UUID REFERENCES battle_decks(id),
  winner_id UUID REFERENCES users(id),
  player1_score INTEGER NOT NULL,
  player2_score INTEGER NOT NULL,
  player1_tokens INTEGER DEFAULT 0,
  player2_tokens INTEGER DEFAULT 0,
  is_surrender BOOLEAN DEFAULT FALSE,
  is_ai_game BOOLEAN DEFAULT FALSE,
  game_log JSONB, -- Full game log
  played_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_games_player1 ON games(player1_id);
CREATE INDEX idx_games_player2 ON games(player2_id);
CREATE INDEX idx_games_played_at ON games(played_at DESC);

-- ============================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE decks ENABLE ROW LEVEL SECURITY;
ALTER TABLE battle_decks ENABLE ROW LEVEL SECURITY;
ALTER TABLE games ENABLE ROW LEVEL SECURITY;

-- Users: can read all, update own
CREATE POLICY "Users can view all users" ON users
  FOR SELECT USING (true);

CREATE POLICY "Users can update own profile" ON users
  FOR UPDATE USING (auth.uid() = id);

-- Cards: can read all, CRUD own
CREATE POLICY "Anyone can view cards" ON cards
  FOR SELECT USING (true);

CREATE POLICY "Users can insert own cards" ON cards
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own cards" ON cards
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own cards" ON cards
  FOR DELETE USING (auth.uid() = user_id);

-- Decks: can read all, CRUD own
CREATE POLICY "Anyone can view decks" ON decks
  FOR SELECT USING (true);

CREATE POLICY "Users can insert own decks" ON decks
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own decks" ON decks
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own decks" ON decks
  FOR DELETE USING (auth.uid() = user_id);

-- Battle Decks: can read all, CRUD own
CREATE POLICY "Anyone can view battle decks" ON battle_decks
  FOR SELECT USING (true);

CREATE POLICY "Users can insert own battle decks" ON battle_decks
  FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own battle decks" ON battle_decks
  FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own battle decks" ON battle_decks
  FOR DELETE USING (auth.uid() = user_id);

-- Games: can read all, insert own
CREATE POLICY "Anyone can view games" ON games
  FOR SELECT USING (true);

CREATE POLICY "Users can insert games" ON games
  FOR INSERT WITH CHECK (auth.uid() = player1_id);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at
  BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_cards_updated_at
  BEFORE UPDATE ON cards
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_decks_updated_at
  BEFORE UPDATE ON decks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_battle_decks_updated_at
  BEFORE UPDATE ON battle_decks
  FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Function to add XP to cards after game
CREATE OR REPLACE FUNCTION add_card_xp(
  p_user_id UUID,
  p_card_ids UUID[],
  p_xp_amount INTEGER,
  p_is_win BOOLEAN
)
RETURNS void AS $$
BEGIN
  UPDATE cards
  SET 
    xp = xp + p_xp_amount,
    games_played = games_played + 1,
    wins = wins + CASE WHEN p_is_win THEN 1 ELSE 0 END
  WHERE id = ANY(p_card_ids)
    AND user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- VIEWS
-- ============================================

-- Leaderboard view
CREATE VIEW leaderboard AS
SELECT 
  u.id,
  u.username,
  u.avatar_url,
  COUNT(g.id) FILTER (WHERE g.winner_id = u.id) as wins,
  COUNT(g.id) as total_games,
  ROUND(
    COUNT(g.id) FILTER (WHERE g.winner_id = u.id)::NUMERIC / 
    NULLIF(COUNT(g.id), 0) * 100, 1
  ) as win_rate
FROM users u
LEFT JOIN games g ON g.player1_id = u.id OR g.player2_id = u.id
GROUP BY u.id
ORDER BY wins DESC, win_rate DESC;
