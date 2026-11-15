"""Read-only access for the UI layer. Screens import this module instead of touching the database directly."""
from database.repositories import (  # noqa: F401
    all_tests, approvals, comments, conflict_sides, document_versions, findings, get_fact, get_rule, get_submission,
    latest_report, latest_test, list_conflicts, list_decisions, list_documents, list_facts, list_rules, list_submissions,
    list_terms, list_workspaces, open_conflicts_for_rule, passage, products, recent_activity, revisions, rule_revisions,
    test_cases, tests_for_rule, user, users,
)
from database.repositories import get_or_create_user, get_or_create_workspace  # noqa: F401
from database.repositories import decisions_for_submission, finding, passages_at, rule_links, source_page, doc_pages  # noqa: F401
