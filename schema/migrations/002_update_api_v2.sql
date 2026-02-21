-- 002_update_api_v2.sql
-- Update schema to match current Riot TFT API (2025+)
-- Changes: league entries no longer have summonerId, participants have riotId + win,
-- unit_items no longer has integer item_id, augments are optional (not in Set 16)

-- league_entries: remove summoner_id, add unique constraint for upserts
ALTER TABLE league_entries DROP COLUMN IF EXISTS summoner_id;
ALTER TABLE league_entries ADD CONSTRAINT uq_league_entries_puuid_region UNIQUE (puuid, region);

-- match_participants: add new fields from current API
ALTER TABLE match_participants ADD COLUMN IF NOT EXISTS riot_id_game_name VARCHAR(128);
ALTER TABLE match_participants ADD COLUMN IF NOT EXISTS riot_id_tagline VARCHAR(64);
ALTER TABLE match_participants ADD COLUMN IF NOT EXISTS win BOOLEAN;

-- unit_items: item_id is no longer provided by API, make nullable
ALTER TABLE unit_items ALTER COLUMN item_id DROP NOT NULL;
