-- 003_widen_columns.sql
-- Widen string columns to handle actual API data lengths

ALTER TABLE matches ALTER COLUMN game_version TYPE VARCHAR(256);
ALTER TABLE matches ALTER COLUMN tft_set_core_name TYPE VARCHAR(128);
