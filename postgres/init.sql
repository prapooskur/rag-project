CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS discord_text (
	message_id TEXT PRIMARY KEY,
	channel_id TEXT NOT NULL,
	server_id TEXT NOT NULL,
	sender_id TEXT NOT NULL,
	sender_username TEXT NOT NULL,
	sender_nickname TEXT,
	channel_name TEXT NOT NULL,
	content TEXT NOT NULL,
	created_at TIMESTAMPTZ NOT NULL,
	ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_discord_text_server_channel ON discord_text (server_id, channel_id);
CREATE INDEX IF NOT EXISTS idx_discord_text_sender ON discord_text (sender_id);
CREATE INDEX IF NOT EXISTS idx_discord_text_created_at ON discord_text (message_created_at);