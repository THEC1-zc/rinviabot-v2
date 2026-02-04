// ============================================
// TOKEN-CCG Supabase Client
// Version: 1.0.0
// ============================================

const SUPABASE_URL = 'https://fyuqowfoklelfyzgndga.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ5dXFvd2Zva2xlbGZ5emduZGdhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzg2NTk2MDAsImV4cCI6MjA1NDIzNTYwMH0.YOUR_KEY_HERE';

// Initialize Supabase client
// Include this in your HTML: <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
let supabase = null;

function initSupabase() {
  if (typeof window !== 'undefined' && window.supabase) {
    supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    console.log('Supabase initialized');
    return supabase;
  }
  console.error('Supabase JS not loaded');
  return null;
}

// ============================================
// AUTH FUNCTIONS
// ============================================

// Get current user
async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

// Sign in with wallet (custom flow)
async function signInWithWallet(walletAddress) {
  // First check if user exists
  let { data: user } = await supabase
    .from('users')
    .select('*')
    .eq('wallet_address', walletAddress)
    .single();
  
  if (!user) {
    // Create new user
    const { data: newUser, error } = await supabase
      .from('users')
      .insert({ wallet_address: walletAddress })
      .select()
      .single();
    
    if (error) throw error;
    user = newUser;
  }
  
  return user;
}

// Sign in with Farcaster
async function signInWithFarcaster(fid, username, avatarUrl) {
  let { data: user } = await supabase
    .from('users')
    .select('*')
    .eq('farcaster_fid', fid)
    .single();
  
  if (!user) {
    const { data: newUser, error } = await supabase
      .from('users')
      .insert({ 
        farcaster_fid: fid,
        username: username,
        avatar_url: avatarUrl
      })
      .select()
      .single();
    
    if (error) throw error;
    user = newUser;
  }
  
  return user;
}

// ============================================
// CARDS FUNCTIONS
// ============================================

// Get all cards for a user
async function getUserCards(userId) {
  const { data, error } = await supabase
    .from('cards')
    .select('*')
    .eq('user_id', userId)
    .order('house')
    .order('value');
  
  if (error) throw error;
  return data;
}

// Create a new card
async function createCard(userId, cardData) {
  const { data, error } = await supabase
    .from('cards')
    .insert({
      user_id: userId,
      house: cardData.house,
      faction_name: cardData.factionName,
      faction_icon: cardData.factionIcon,
      value: cardData.value,
      display_value: cardData.displayValue,
      card_name: cardData.cardName
    })
    .select()
    .single();
  
  if (error) {
    if (error.code === '23505') {
      throw new Error('Card with this value already exists in this faction');
    }
    throw error;
  }
  return data;
}

// Update card XP
async function updateCardXP(cardId, xpToAdd) {
  const { data, error } = await supabase
    .from('cards')
    .update({ xp: supabase.rpc('increment', { x: xpToAdd }) })
    .eq('id', cardId)
    .select()
    .single();
  
  if (error) throw error;
  return data;
}

// Delete a card
async function deleteCard(cardId) {
  const { error } = await supabase
    .from('cards')
    .delete()
    .eq('id', cardId);
  
  if (error) throw error;
}

// ============================================
// DECKS FUNCTIONS
// ============================================

// Get all decks for a user
async function getUserDecks(userId) {
  const { data, error } = await supabase
    .from('decks')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });
  
  if (error) throw error;
  return data;
}

// Create a new deck
async function createDeck(userId, deckData) {
  const { data, error } = await supabase
    .from('decks')
    .insert({
      user_id: userId,
      house: deckData.house,
      faction_name: deckData.factionName,
      faction_icon: deckData.factionIcon,
      cards: deckData.cards
    })
    .select()
    .single();
  
  if (error) throw error;
  return data;
}

// Delete a deck
async function deleteDeck(deckId) {
  const { error } = await supabase
    .from('decks')
    .delete()
    .eq('id', deckId);
  
  if (error) throw error;
}

// ============================================
// BATTLE DECKS FUNCTIONS
// ============================================

// Get all battle decks for a user
async function getUserBattleDecks(userId) {
  const { data, error } = await supabase
    .from('battle_decks')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false });
  
  if (error) throw error;
  return data;
}

// Create a battle deck
async function createBattleDeck(userId, battleDeckData) {
  const { data, error } = await supabase
    .from('battle_decks')
    .insert({
      user_id: userId,
      name: battleDeckData.name,
      deck1_house: battleDeckData.deck1House,
      deck2_house: battleDeckData.deck2House,
      deck1_cards: battleDeckData.deck1Cards,
      deck2_cards: battleDeckData.deck2Cards
    })
    .select()
    .single();
  
  if (error) throw error;
  return data;
}

// Delete a battle deck
async function deleteBattleDeck(battleDeckId) {
  const { error } = await supabase
    .from('battle_decks')
    .delete()
    .eq('id', battleDeckId);
  
  if (error) throw error;
}

// ============================================
// GAMES FUNCTIONS
// ============================================

// Record a game result
async function recordGame(gameData) {
  const { data, error } = await supabase
    .from('games')
    .insert({
      player1_id: gameData.player1Id,
      player2_id: gameData.player2Id,
      player1_battle_deck_id: gameData.player1BattleDeckId,
      player2_battle_deck_id: gameData.player2BattleDeckId,
      winner_id: gameData.winnerId,
      player1_score: gameData.player1Score,
      player2_score: gameData.player2Score,
      player1_tokens: gameData.player1Tokens,
      player2_tokens: gameData.player2Tokens,
      is_surrender: gameData.isSurrender || false,
      is_ai_game: gameData.isAiGame || false,
      game_log: gameData.gameLog
    })
    .select()
    .single();
  
  if (error) throw error;
  return data;
}

// Get user game history
async function getUserGames(userId, limit = 20) {
  const { data, error } = await supabase
    .from('games')
    .select('*')
    .or(`player1_id.eq.${userId},player2_id.eq.${userId}`)
    .order('played_at', { ascending: false })
    .limit(limit);
  
  if (error) throw error;
  return data;
}

// Get leaderboard
async function getLeaderboard(limit = 100) {
  const { data, error } = await supabase
    .from('leaderboard')
    .select('*')
    .limit(limit);
  
  if (error) throw error;
  return data;
}

// ============================================
// MIGRATION FROM LOCALSTORAGE
// ============================================

async function migrateFromLocalStorage(userId) {
  const results = {
    cards: 0,
    decks: 0,
    battleDecks: 0,
    errors: []
  };
  
  try {
    // Migrate single cards
    const localCards = JSON.parse(localStorage.getItem('token_cards') || '[]');
    for (const card of localCards) {
      try {
        await createCard(userId, {
          house: card.house,
          factionName: card.factionName || 'Unknown',
          factionIcon: card.factionIcon || '🎴',
          value: parseInt(card.value),
          displayValue: card.displayValue,
          cardName: card.cardName
        });
        results.cards++;
      } catch (e) {
        results.errors.push(`Card ${card.displayValue}: ${e.message}`);
      }
    }
    
    // Migrate decks
    const localDecks = JSON.parse(localStorage.getItem('token_decks') || '[]');
    for (const deck of localDecks) {
      try {
        await createDeck(userId, {
          house: deck.house,
          factionName: deck.faction || 'Unknown',
          factionIcon: deck.factionIcon || '🎴',
          cards: deck.cards
        });
        results.decks++;
      } catch (e) {
        results.errors.push(`Deck ${deck.faction}: ${e.message}`);
      }
    }
    
    // Migrate battle decks
    const localBattleDecks = JSON.parse(localStorage.getItem('token_battle_decks') || '[]');
    for (const bd of localBattleDecks) {
      try {
        await createBattleDeck(userId, {
          name: bd.name,
          deck1House: bd.deck1House,
          deck2House: bd.deck2House,
          deck1Cards: bd.deck1Cards,
          deck2Cards: bd.deck2Cards
        });
        results.battleDecks++;
      } catch (e) {
        results.errors.push(`Battle Deck ${bd.name}: ${e.message}`);
      }
    }
    
  } catch (e) {
    results.errors.push(`Migration error: ${e.message}`);
  }
  
  return results;
}

// ============================================
// EXPORT
// ============================================

// For use in browser
if (typeof window !== 'undefined') {
  window.TokenDB = {
    init: initSupabase,
    // Auth
    getCurrentUser,
    signInWithWallet,
    signInWithFarcaster,
    // Cards
    getUserCards,
    createCard,
    updateCardXP,
    deleteCard,
    // Decks
    getUserDecks,
    createDeck,
    deleteDeck,
    // Battle Decks
    getUserBattleDecks,
    createBattleDeck,
    deleteBattleDeck,
    // Games
    recordGame,
    getUserGames,
    getLeaderboard,
    // Migration
    migrateFromLocalStorage
  };
}
