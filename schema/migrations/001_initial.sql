-- 001_initial.sql
-- TFT Analytics Schema

CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(64) PRIMARY KEY,
    data_version VARCHAR(8),
    game_datetime BIGINT,
    game_length REAL,
    game_version VARCHAR(64),
    queue_id INT,
    tft_game_type VARCHAR(32),
    tft_set_number INT,
    tft_set_core_name VARCHAR(64),
    region VARCHAR(16),
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS match_participants (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(64) REFERENCES matches(match_id),
    puuid VARCHAR(128),
    placement INT,
    level INT,
    gold_left INT,
    last_round INT,
    players_eliminated INT,
    time_eliminated REAL,
    total_damage_to_players INT
);

CREATE TABLE IF NOT EXISTS participant_augments (
    id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES match_participants(id),
    augment_id VARCHAR(128),
    pick_order INT
);

CREATE TABLE IF NOT EXISTS participant_traits (
    id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES match_participants(id),
    trait_name VARCHAR(128),
    num_units INT,
    tier_current INT,
    tier_total INT,
    style INT
);

CREATE TABLE IF NOT EXISTS participant_units (
    id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES match_participants(id),
    character_id VARCHAR(128),
    tier INT,
    rarity INT
);

CREATE TABLE IF NOT EXISTS unit_items (
    id SERIAL PRIMARY KEY,
    unit_id INT REFERENCES participant_units(id),
    item_id INT,
    item_name VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS league_entries (
    id SERIAL PRIMARY KEY,
    summoner_id VARCHAR(128),
    puuid VARCHAR(128),
    tier VARCHAR(16),
    rank VARCHAR(8),
    league_points INT,
    wins INT,
    losses INT,
    region VARCHAR(16),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_match_participants_match_id ON match_participants(match_id);
CREATE INDEX IF NOT EXISTS idx_match_participants_puuid ON match_participants(puuid);
CREATE INDEX IF NOT EXISTS idx_participant_augments_participant_id ON participant_augments(participant_id);
CREATE INDEX IF NOT EXISTS idx_participant_traits_participant_id ON participant_traits(participant_id);
CREATE INDEX IF NOT EXISTS idx_participant_units_participant_id ON participant_units(participant_id);
CREATE INDEX IF NOT EXISTS idx_unit_items_unit_id ON unit_items(unit_id);
CREATE INDEX IF NOT EXISTS idx_matches_region ON matches(region);
CREATE INDEX IF NOT EXISTS idx_matches_tft_set_number ON matches(tft_set_number);
CREATE INDEX IF NOT EXISTS idx_league_entries_puuid ON league_entries(puuid);
CREATE INDEX IF NOT EXISTS idx_league_entries_region ON league_entries(region);
