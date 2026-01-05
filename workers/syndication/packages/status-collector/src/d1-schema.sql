CREATE TABLE IF NOT EXISTS executions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  site TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  articles_processed INTEGER DEFAULT 0,
  success_count INTEGER DEFAULT 0,
  failure_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS platform_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  execution_id INTEGER NOT NULL,
  article_url TEXT NOT NULL,
  article_title TEXT,
  platform TEXT NOT NULL,
  success INTEGER NOT NULL,
  result_url TEXT,
  error TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (execution_id) REFERENCES executions(id)
);

CREATE INDEX IF NOT EXISTS idx_executions_site ON executions(site);
CREATE INDEX IF NOT EXISTS idx_executions_timestamp ON executions(timestamp);
CREATE INDEX IF NOT EXISTS idx_platform_results_platform ON platform_results(platform);

