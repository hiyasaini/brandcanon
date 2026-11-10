-- BrandCanon relational schema (SQLite). Version 3 (v2: users.password_hash; v3: document review status, RuleProbe investigation states).
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL, applied_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS workspaces (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  is_demo INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0, 1)),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('Creator', 'Reviewer', 'Brand Manager')),
  password_hash TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (workspace_id, name, role)
);

-- A logical document (e.g. "Product Specifications") with one or more uploaded versions.
CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  authority_level TEXT NOT NULL,
  authority_rank INTEGER NOT NULL CHECK (authority_rank BETWEEN 0 AND 5),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  review_status TEXT NOT NULL DEFAULT 'Pending review'
    CHECK (review_status IN ('Pending review', 'Approved', 'Rejected', 'Archived')),
  review_note TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (workspace_id, title)
);

CREATE TABLE IF NOT EXISTS document_versions (
  id INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  version_label TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_size INTEGER NOT NULL CHECK (file_size >= 0),
  sha256 TEXT NOT NULL,
  source_url TEXT,
  effective_date TEXT,
  page_count INTEGER NOT NULL DEFAULT 0,
  extraction_status TEXT NOT NULL CHECK (extraction_status IN ('extracted', 'empty', 'failed')),
  extraction_engine TEXT,
  injection_flags INTEGER NOT NULL DEFAULT 0,
  is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
  uploaded_by INTEGER REFERENCES users(id),
  uploaded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_docver_doc ON document_versions(document_id);

-- Exact extracted text, kept so every citation points at stored text.
CREATE TABLE IF NOT EXISTS passages (
  id INTEGER PRIMARY KEY,
  version_id INTEGER NOT NULL REFERENCES document_versions(id) ON DELETE CASCADE,
  location TEXT NOT NULL,          -- "p.3" or "§2"
  seq INTEGER NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_passage_ver ON passages(version_id);

CREATE TABLE IF NOT EXISTS brand_rules (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  code TEXT NOT NULL,
  text TEXT NOT NULL,
  category TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'All content',
  rule_version INTEGER NOT NULL DEFAULT 1,
  version_id INTEGER REFERENCES document_versions(id) ON DELETE CASCADE,
  passage_id INTEGER REFERENCES passages(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'Pending Validation'
    CHECK (status IN ('Pending Validation', 'Approved', 'Rejected', 'Needs Clarification', 'Archived')),
  approved_by INTEGER REFERENCES users(id),
  approved_at TEXT,
  constraints_json TEXT NOT NULL DEFAULT '{}',   -- machine-checkable parts parsed from the text
  clarity TEXT NOT NULL DEFAULT 'Untested',
  divergence REAL,
  extracted_by TEXT NOT NULL DEFAULT 'deterministic',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (workspace_id, code)
);
CREATE INDEX IF NOT EXISTS ix_rule_ws ON brand_rules(workspace_id, status);

CREATE TABLE IF NOT EXISTS rule_revisions (
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL REFERENCES brand_rules(id) ON DELETE CASCADE,
  rule_version INTEGER NOT NULL,
  text TEXT NOT NULL,
  scope TEXT NOT NULL,
  changed_by INTEGER REFERENCES users(id),
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_rulerev_rule ON rule_revisions(rule_id);

CREATE TABLE IF NOT EXISTS brand_facts (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  product TEXT NOT NULL,
  attribute TEXT NOT NULL,
  value REAL NOT NULL,
  unit TEXT NOT NULL,
  qualifier TEXT NOT NULL DEFAULT '',
  raw_text TEXT NOT NULL,
  version_id INTEGER REFERENCES document_versions(id) ON DELETE CASCADE,
  passage_id INTEGER REFERENCES passages(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'Pending Validation'
    CHECK (status IN ('Pending Validation', 'Approved', 'Rejected', 'Superseded', 'Archived')),
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_fact_ws ON brand_facts(workspace_id, product, attribute);

CREATE TABLE IF NOT EXISTS terms (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  term TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('prohibited', 'preferred')),
  replacement TEXT NOT NULL DEFAULT '',
  rule_id INTEGER REFERENCES brand_rules(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL,
  UNIQUE (workspace_id, term, kind)
);

CREATE TABLE IF NOT EXISTS rule_tests (
  id INTEGER PRIMARY KEY,
  rule_id INTEGER NOT NULL REFERENCES brand_rules(id) ON DELETE CASCADE,
  rule_version INTEGER NOT NULL,
  context TEXT NOT NULL,
  engine TEXT NOT NULL,
  classification TEXT NOT NULL
    CHECK (classification IN ('Ambiguous rule', 'Contradictory rules', 'Missing guidance', 'Model uncertainty', 'Clear rule')),
  issue TEXT NOT NULL,
  recommendation TEXT NOT NULL DEFAULT '',
  divergence REAL NOT NULL DEFAULT 0,
  self_inconsistency REAL NOT NULL DEFAULT 0,
  requires_human_review INTEGER NOT NULL DEFAULT 1 CHECK (requires_human_review IN (0, 1)),
  related_rule_ids TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  investigation_state TEXT NOT NULL DEFAULT 'draft'
    CHECK (investigation_state IN ('draft', 'saved', 'in_review', 'approved', 'rule_updated')),
  notes TEXT,
  resolution TEXT,
  resolution_note TEXT,
  resolved_by INTEGER REFERENCES users(id),
  resolved_at TEXT,
  run_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_test_rule ON rule_tests(rule_id);

CREATE TABLE IF NOT EXISTS rule_test_cases (
  id INTEGER PRIMARY KEY,
  test_id INTEGER NOT NULL REFERENCES rule_tests(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  dimension TEXT NOT NULL,
  level INTEGER NOT NULL,
  example TEXT NOT NULL,
  strict_verdict TEXT NOT NULL CHECK (strict_verdict IN ('pass', 'fail', 'unclear')),
  strict_reason TEXT NOT NULL,
  lenient_verdict TEXT NOT NULL CHECK (lenient_verdict IN ('pass', 'fail', 'unclear')),
  lenient_reason TEXT NOT NULL,
  assessment TEXT NOT NULL,
  confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  reviewer_mark TEXT CHECK (reviewer_mark IN ('correct', 'incorrect', 'inconclusive')),
  marked_by INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_case_test ON rule_test_cases(test_id);

CREATE TABLE IF NOT EXISTS source_conflicts (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('fact', 'rule')),
  signature TEXT NOT NULL,
  title TEXT NOT NULL,
  explanation TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  resolution TEXT,
  resolution_note TEXT,
  resolved_by INTEGER REFERENCES users(id),
  resolved_at TEXT,
  created_at TEXT NOT NULL,
  UNIQUE (workspace_id, signature)
);

CREATE TABLE IF NOT EXISTS conflict_sides (
  id INTEGER PRIMARY KEY,
  conflict_id INTEGER NOT NULL REFERENCES source_conflicts(id) ON DELETE CASCADE,
  rule_id INTEGER REFERENCES brand_rules(id) ON DELETE CASCADE,
  fact_id INTEGER REFERENCES brand_facts(id) ON DELETE CASCADE,
  CHECK ((rule_id IS NULL) != (fact_id IS NULL))
);

CREATE TABLE IF NOT EXISTS content_submissions (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  content_type TEXT NOT NULL,
  channel TEXT NOT NULL,
  product TEXT,
  campaign TEXT,
  author_id INTEGER REFERENCES users(id),
  status TEXT NOT NULL DEFAULT 'Draft'
    CHECK (status IN ('Draft', 'In review', 'Changes requested', 'Escalated', 'Approved', 'Rejected')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sub_ws ON content_submissions(workspace_id, status);

CREATE TABLE IF NOT EXISTS content_revisions (
  id INTEGER PRIMARY KEY,
  submission_id INTEGER NOT NULL REFERENCES content_submissions(id) ON DELETE CASCADE,
  revision_no INTEGER NOT NULL,
  text TEXT NOT NULL,
  alt_text TEXT,
  note TEXT,
  created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL,
  UNIQUE (submission_id, revision_no)
);

CREATE TABLE IF NOT EXISTS audit_reports (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  revision_id INTEGER REFERENCES content_revisions(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  content_type TEXT NOT NULL,
  product TEXT,
  engine TEXT NOT NULL,
  overall_status TEXT NOT NULL CHECK (overall_status IN ('Changes needed', 'Review suggested', 'No issues found')),
  n_high INTEGER NOT NULL DEFAULT 0,
  n_medium INTEGER NOT NULL DEFAULT 0,
  n_low INTEGER NOT NULL DEFAULT 0,
  created_by INTEGER REFERENCES users(id),
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_report_rev ON audit_reports(revision_id);

CREATE TABLE IF NOT EXISTS audit_findings (
  id INTEGER PRIMARY KEY,
  report_id INTEGER NOT NULL REFERENCES audit_reports(id) ON DELETE CASCADE,
  seq INTEGER NOT NULL,
  category TEXT NOT NULL,
  classification TEXT NOT NULL
    CHECK (classification IN ('Contradicted', 'Unsupported', 'Unverifiable', 'Verified', 'Violation', 'Needs review')),
  severity TEXT NOT NULL CHECK (severity IN ('high', 'medium', 'low', 'info')),
  span_start INTEGER,
  span_end INTEGER,
  quote TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL,
  suggestion TEXT NOT NULL DEFAULT '',
  rule_id INTEGER REFERENCES brand_rules(id) ON DELETE SET NULL,
  fact_id INTEGER REFERENCES brand_facts(id) ON DELETE SET NULL,
  passage_id INTEGER REFERENCES passages(id) ON DELETE SET NULL,
  evidence_text TEXT NOT NULL DEFAULT '',
  evidence_source TEXT NOT NULL DEFAULT '',
  root_cause TEXT NOT NULL
    CHECK (root_cause IN ('Creator error', 'Guideline defect', 'Source conflict', 'Knowledge gap', 'Unresolved / other', 'Not applicable')),
  confidence TEXT NOT NULL CHECK (confidence IN ('high', 'medium', 'low')),
  engine TEXT NOT NULL,
  disposition TEXT NOT NULL DEFAULT 'open' CHECK (disposition IN ('open', 'accepted', 'edited', 'dismissed')),
  disposition_reason TEXT,
  disposed_by INTEGER REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS ix_finding_report ON audit_findings(report_id);

CREATE TABLE IF NOT EXISTS decisions (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  submission_id INTEGER REFERENCES content_submissions(id) ON DELETE CASCADE,
  revision_id INTEGER REFERENCES content_revisions(id) ON DELETE CASCADE,
  finding_id INTEGER REFERENCES audit_findings(id) ON DELETE SET NULL,
  rule_id INTEGER REFERENCES brand_rules(id) ON DELETE SET NULL,
  fact_id INTEGER REFERENCES brand_facts(id) ON DELETE SET NULL,
  source_version_id INTEGER REFERENCES document_versions(id) ON DELETE SET NULL,
  decision TEXT NOT NULL CHECK (decision IN ('Approved', 'Changes requested', 'Rejected', 'Escalated', 'Finding upheld', 'Finding overridden')),
  claim_text TEXT NOT NULL DEFAULT '',
  finding_category TEXT,
  explanation TEXT NOT NULL CHECK (length(trim(explanation)) > 0),
  approved_correction TEXT,
  channel TEXT,
  product TEXT,
  campaign TEXT,
  reviewer_id INTEGER REFERENCES users(id),
  supersedes_decision_id INTEGER REFERENCES decisions(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_decision_ws ON decisions(workspace_id, product, channel);

CREATE TABLE IF NOT EXISTS approvals (
  id INTEGER PRIMARY KEY,
  submission_id INTEGER NOT NULL REFERENCES content_submissions(id) ON DELETE CASCADE,
  revision_id INTEGER NOT NULL REFERENCES content_revisions(id) ON DELETE CASCADE,
  outcome TEXT NOT NULL CHECK (outcome IN ('Approved', 'Changes requested', 'Rejected', 'Escalated')),
  rationale TEXT NOT NULL CHECK (length(trim(rationale)) > 0),
  reviewer_id INTEGER NOT NULL REFERENCES users(id),
  decision_id INTEGER REFERENCES decisions(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY,
  submission_id INTEGER NOT NULL REFERENCES content_submissions(id) ON DELETE CASCADE,
  revision_no INTEGER,
  user_id INTEGER REFERENCES users(id),
  text TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
  id INTEGER PRIMARY KEY,
  workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id INTEGER REFERENCES users(id),
  action TEXT NOT NULL,
  entity_type TEXT,
  entity_id INTEGER,
  detail TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_log_ws ON activity_log(workspace_id, created_at);

CREATE TABLE IF NOT EXISTS llm_cache (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  created_at TEXT NOT NULL
);
