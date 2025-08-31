PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS issues (
  issue_id        TEXT PRIMARY KEY,
  source          TEXT NOT NULL,
  source_rule_id  TEXT,
  language        TEXT,
  title           TEXT NOT NULL,
  summary         TEXT,
  fix_steps       TEXT,
  severity        TEXT,
  confidence      REAL,
  taxonomy_json   TEXT,
  frequency       INTEGER,
  metadata_json   TEXT,
  updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS signals (
  issue_id  TEXT NOT NULL,
  kind      TEXT,
  value     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS references_web (
  issue_id  TEXT NOT NULL,
  label     TEXT,
  url       TEXT NOT NULL,
  license   TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS fts_issues
USING fts5(
  title, summary, fix_steps, signals_concat, language,
  content='',
  tokenize='porter',
  prefix='2,3,4'
);
