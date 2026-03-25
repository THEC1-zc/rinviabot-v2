CREATE TABLE IF NOT EXISTS pipeline_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  trace_id TEXT NOT NULL,
  stage TEXT NOT NULL,
  chat_id TEXT,
  message_id TEXT,
  user_id TEXT,
  username TEXT,
  text_preview TEXT,
  source TEXT NOT NULL DEFAULT 'rinviabot',
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_trace_id
ON pipeline_events(trace_id);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_stage
ON pipeline_events(stage);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_ts
ON pipeline_events(ts);

CREATE INDEX IF NOT EXISTS idx_pipeline_events_message
ON pipeline_events(chat_id, message_id);

