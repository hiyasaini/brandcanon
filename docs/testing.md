# Testing

All results below come from real runs. `bash scripts/run_tests.sh` re-runs the mocked suite and overwrites `docs/test_results.txt`; `bash scripts/run_live_tests.sh` runs the live Gemini smoke tests and writes `docs/live_test_results.txt`.

## Automated tests (pytest): 100 passed, 4 deselected

Each test uses its own temporary database. The mocked suite never contacts Gemini: Gemini is either forced off or replaced with fakes that return fixed JSON or raise the SDK's own error types. The 4 deselected tests are the live smoke tests, excluded from the default run. Full output: `docs/test_results.txt`.

### Sign-in

| Test | Result |
|---|---|
| `test_hash_is_salted_and_verifies` | PASSED |
| `test_workspace_creation_and_sign_in` | PASSED |
| `test_only_brand_manager_adds_people` | PASSED |
| `test_legacy_account_activation` | PASSED |
| `test_demo_accounts_have_demo_password` | PASSED |
| `test_migration_from_v1_adds_password_column` | PASSED |

### Document ingestion (PDF and DOCX only)

| Test | Result |
|---|---|
| `test_pdf_extraction_preserves_pages` | PASSED |
| `test_docx_extraction` | PASSED |
| `test_empty_document_adds_nothing` | PASSED |
| `test_unreadable_pdf_is_reported` | PASSED |
| `test_unsupported_type_and_fake_signature_rejected` | PASSED |
| `test_prompt_injection_is_flagged_and_kept_as_data` | PASSED |
| `test_new_version_archives_previous_rules` | PASSED |
| `test_only_brand_manager_can_upload` | PASSED |
| `test_only_pdf_and_docx_are_accepted` | PASSED |

### Brand Constitution (documents, rules, versions)

| Test | Result |
|---|---|
| `test_rule_approval_rejection_and_permissions` | PASSED |
| `test_rule_edit_creates_version_and_revision` | PASSED |
| `test_rules_keep_document_version` | PASSED |
| `test_delete_document_cleans_up` | PASSED |
| `test_document_review_does_not_auto_approve_rules` | PASSED |
| `test_new_version_needs_review_again_and_compares` | PASSED |

### Conflicts and missing guidance

| Test | Result |
|---|---|
| `test_battery_conflict_detected_with_both_sources` | PASSED |
| `test_resolving_fact_conflict_supersedes_other_value` | PASSED |
| `test_rule_conflict_needs_overlapping_scope` | PASSED |
| `test_rescope_resolves_rule_conflict` | PASSED |
| `test_coverage_gaps_report_missing_guidance` | PASSED |

### RuleProbe (tests and investigation workflow)

| Test | Result |
|---|---|
| `test_controlled_cases_change_one_characteristic` | PASSED |
| `test_vague_tone_rule_is_classified_ambiguous` | PASSED |
| `test_clarification_removes_divergence_and_keeps_history` | PASSED |
| `test_missing_guidance_for_out_of_scope_context` | PASSED |
| `test_contradictory_rules_classification` | PASSED |
| `test_measurable_rule_is_clear` | PASSED |
| `test_model_uncertainty_is_separate_from_ambiguity` | PASSED |
| `test_reviewer_marks_and_permissions` | PASSED |
| `test_investigation_workflow_and_labels` | PASSED |
| `test_manual_and_edited_cases` | PASSED |

### Content Auditor

| Test | Result |
|---|---|
| `test_supported_claim_is_verified` | PASSED |
| `test_contradicted_numeric_claim_cites_page` | PASSED |
| `test_unsupported_promotional_claim` | PASSED |
| `test_missing_qualifier` | PASSED |
| `test_terminology_violation` | PASSED |
| `test_tone_mismatch` | PASSED |
| `test_superlative_without_evidence_is_unverifiable_not_false` | PASSED |
| `test_missing_evidence_is_a_knowledge_gap` | PASSED |
| `test_apply_suggestions_keeps_message` | PASSED |
| `test_visual_audit_checks` | PASSED |

### Approval workflow, governance and demo

| Test | Result |
|---|---|
| `test_full_novatech_workflow` | PASSED |
| `test_governance_aggregation_matches_records` | PASSED |
| `test_empty_workspace_and_date_filter` | PASSED |
| `test_untrusted_wrapping_and_redaction` | PASSED |
| `test_demo_reset_builds_real_records` | PASSED |
| `test_dismissal_carries_to_next_revision` | PASSED |

### Decision Memory

| Test | Result |
|---|---|
| `test_decisions_are_saved` | PASSED |
| `test_precedent_retrieved_for_similar_claim` | PASSED |
| `test_precedent_from_old_source_version_is_flagged` | PASSED |
| `test_decisions_never_change_rules` | PASSED |
| `test_override_supersedes_earlier_decision` | PASSED |
| `test_creator_cannot_approve` | PASSED |

### Round 2 demo views (source page, guided demo, comments)

| Test | Result |
|---|---|
| `test_source_page_shows_the_cited_passage` | PASSED |
| `test_guided_demo_steps_follow_stored_records` | PASSED |
| `test_comments_are_stored_per_revision` | PASSED |

### Redesign backend (manual rules, knowledge graph, search, review time)

| Test | Result |
|---|---|
| `test_manual_rule_is_pending_unless_approved` | PASSED |
| `test_graph_uses_only_stored_records` | PASSED |
| `test_graph_filters_layouts_and_neighbours` | PASSED |
| `test_global_search_finds_stored_text_only` | PASSED |
| `test_average_review_time` | PASSED |

### Gemini integration (mocked: no network)

| Test | Result |
|---|---|
| `test_provider_selection` | PASSED |
| `test_demo_suspension_labels_demo_fallback` | PASSED |
| `test_malformed_output_retried_then_rejected` | PASSED |
| `test_cache_is_labelled_as_cached` | PASSED |
| `test_errors_are_classified_and_reported[exc0-invalid_key]` | PASSED |
| `test_errors_are_classified_and_reported[exc1-invalid_key]` | PASSED |
| `test_errors_are_classified_and_reported[exc2-quota]` | PASSED |
| `test_errors_are_classified_and_reported[exc3-model_unavailable]` | PASSED |
| `test_errors_are_classified_and_reported[exc4-service]` | PASSED |
| `test_errors_are_classified_and_reported[exc5-rejected]` | PASSED |
| `test_errors_are_classified_and_reported[exc6-network]` | PASSED |
| `test_errors_are_classified_and_reported[exc7-network]` | PASSED |
| `test_errors_are_classified_and_reported[exc8-unknown]` | PASSED |
| `test_busy_service_is_retried_then_succeeds` | PASSED |
| `test_retries_give_up_and_report_attempts` | PASSED |
| `test_quota_errors_are_not_retried` | PASSED |
| `test_api_key_never_appears_in_errors` | PASSED |
| `test_check_connection_reports_failure_without_key` | PASSED |
| `test_check_connection_success` | PASSED |
| `test_audit_reports_gemini_failure` | PASSED |
| `test_audit_when_gemini_requested_but_not_configured` | PASSED |
| `test_audit_with_live_gemini_findings_validated` | PASSED |
| `test_extraction_failure_is_reported` | PASSED |
| `test_extraction_with_gemini_keeps_only_text_in_document` | PASSED |
| `test_ruleprobe_failure_falls_back_with_label` | PASSED |
| `test_ruleprobe_gemini_generates_cases_for_unknown_words` | PASSED |
| `test_ai_rewrite_is_grounded` | PASSED |
| `test_precedent_summary_rejects_unknown_ids` | PASSED |
| `test_features_refuse_when_gemini_off` | PASSED |
| `test_no_api_keys_committed` | PASSED |
| `test_gemini_switches_on_when_only_a_key_is_set` | PASSED |
| `test_background_check_verifies_without_a_button` | PASSED |
| `test_background_check_not_started_when_gemini_is_off` | PASSED |
| `test_public_mode_flag_and_default_database_path` | PASSED |

## End-to-end browser checks (Playwright, against the running app, after the final change)

### 1 · The NovaTech scenario, AI_PROVIDER=deterministic — 15 steps, all passed, no exceptions, no JavaScript errors

| Step | Result | What was checked |
|---|---|---|
| 01 | PASS | empty NovaTech workspace; Overview guides to upload |
| 02 | PASS | three documents uploaded by hand; extraction reported, everything awaiting review |
| 03 | PASS | authority ≥ 3 approved; the older 15 h presentation stays Pending review |
| 04 | PASS | each rule shows its source passage and page |
| 05 | PASS | RuleProbe shows the potential contradiction: 12 h specification vs 15 h presentation |
| 06 | PASS | tone rule tested: potential finding 'Ambiguous rule' (40% divergence) |
| 07 | PASS | tone guideline clarified as version 2 after authorisation |
| 08 | PASS | source conflict resolved: the specification is the source of truth |
| 09 | PASS | audit: contradicted 15 h claim (spec p.3), unsupported guarantee, exaggerated promise — with evidence |
| 10 | PASS | suggested corrections accepted; intent preserved; before/after shows Current revision · 0 issues |
| 11 | PASS | submitted for approval |
| 12 | PASS | reviewer approved the corrected content |
| 13 | PASS | Decision Memory stores the authorised decision |
| 14 | PASS | Governance reflects the recorded findings and root causes: ['0', '0', '5', '1 min'] where-to-act ['00% of findings', '00% of findings', '3100% of findingslargest share'] |
| 15 | PASS | Overview after the scenario: ['16', '1', '2', '5'] |

Corrected text produced in step 10: *“NovaTech offers up to 12 hours of battery life under specified testing conditions and can support your productivity!”*

### 2 · Every redesigned screen and interaction — 33 checks, all passed, no exceptions, no JavaScript errors

| Check | Result | What was checked |
|---|---|---|
| 01 | PASS | Overview: top bar, four metric cards and the six dashboard cards render |
| 02 | PASS | Pending reviews metric (7) opens Brand Constitution filtered to the same 7 rules |
| 03 | PASS | notification Open navigates and the popover closes |
| 04 | PASS | global search 'battery' → results grouped: Document passages, Audit findings, Content, Product facts, Decisions |
| 05 | PASS | a search result opens its document in Brand Constitution (split workspace) |
| 06 | PASS | document preview shows a stored page: NovaTech Product Specification · v2.0 · p.1 of 4 |
| 07 | PASS | Add brand rule saves a manual rule as Pending review and opens it with 'Added manually' as its source |
| 08 | PASS | the manual rule can be approved |
| 09 | PASS | knowledge category filter (Accessibility · 2) shows 2 items |
| 10 | PASS | Show in graph opens the graph searched for that rule: 2 of 107 nodes  |
| 11 | PASS | clicking a document node shows its stored record and connections |
| 12 | PASS | all four layouts render (circular, hierarchical, grid, force-directed) |
| 13 | PASS | entity filter removes test cases from the graph |
| 14 | PASS | focus on selection: 22 of 107 nodes  |
| 15 | PASS | node 'Open' navigates to the record's screen |
| 16 | PASS | graph search with no match says so |
| 17 | PASS | investigation-type filter (Contradiction) lists 2 rule(s) |
| 18 | PASS | a manual case is added, run and labelled 'Your case' |
| 19 | PASS | investigation map: clicking a node opens its record (Document) |
| 20 | PASS | Save investigation records the state |
| 21 | PASS | Generate test cases discards edits and regenerates the controlled examples |
| 22 | PASS | Conflicts, Missing guidance and Test history tabs render in the dark workspace |
| 23 | PASS | Governance: the six charts render (findings over time, issue categories, root causes, findings by channel, violated rules, reviewer decisions); 'Where to act' opens RuleProbe → Conflicts |
| 24 | PASS | Settings and Help render; profile menu opens Settings |
| 25 | PASS | a DOCX is loaded into the content editor |
| 26 | PASS | 2 finding cards; examining one highlights its phrase |
| 27 | PASS | Edit manually opens the editor |
| 28 | PASS | Dismiss finding with a reason |
| 29 | PASS | Save report downloads brandcanon_audit_8.md |
| 30 | PASS | Re-run audit |
| 31 | PASS | Submit for approval |
| 32 | PASS | decision filters: 1 of 21 decisions  |
| 33 | PASS | selecting a decision opens the dark detail panel with reasoning, evidence trail and history |

### 3 · Guided demo at projector size (1366 × 768), driven only through the stepper — 14 checks, all passed

| Check | Result | What was checked |
|---|---|---|
| 01 | PASS | tour starts on an empty workspace at step 1: ['on', 'todo', 'todo', 'todo', 'todo', 'todo'] |
| 02 | PASS | step 1 ticked from stored approvals → ['done', 'on', 'todo', 'todo', 'todo', 'todo'] |
| 03 | PASS | step 2 ticked after resolving the battery conflict |
| 04 | PASS | step 3 opens RuleProbe on the tone rule |
| 05 | PASS | split view: gauge 40%, 2 split columns, verdict: The rule cannot decide cases #2, #4: one reading passes them and the other fails them. |
| 06 | PASS | step 3 ticked; step 4 asks for Priya |
| 07 | PASS | signed in as Priya with the tour still running |
| 08 | PASS | step 4 opens the auditor with the NovaTech example filled in |
| 09 | PASS | source page shows the cited 12-hour passage highlighted on p.3 |
| 10 | PASS | before/after: First draft · 3 issues → Current revision · 0 issues |
| 11 | PASS | step 4 ticked after submission; step 5 asks for Kavya |
| 12 | PASS | step 5 ticked after Kavya's approval |
| 13 | PASS | step 6 opens Governance 'Where to act': ['00% of findings', '00% of findings', '3100% of findingslargest share'] chips ['done', 'done', 'done', 'done', 'done', 'on'] |
| 14 | PASS | tour ends cleanly |

### 4 · Smoke test of every page as each role

Every page (Overview, Brand Constitution, RuleProbe, Content Auditor, Decision Memory, Governance Intelligence, Knowledge Graph, Settings, Help) was opened as Neha (Brand Manager), Kavya (Reviewer) and Priya (Creator): no exceptions, no error alerts.

Screenshots of the redesigned screens are in `docs/screenshots/`.

### 4b · Layout at laptop widths (1024 px and 1440 px)

Overview, Brand Constitution, RuleProbe, Content Auditor, Decision Memory, Governance Intelligence and Knowledge Graph were captured at 1024 × 2600 and 1440 × 900 after the final layout fixes and inspected: no content outside the workspace panel, multi-panel screens stack below 1180 px, metric cards in a row share one height with their links at the foot, the graph's entity filters wrap instead of being cut off, and sidebar labels wrap instead of being clipped. No JavaScript errors.

### 4c · Every button, as every role (automated click crawler)

A crawler signed in as Neha (Brand Manager), Kavya (Reviewer) and Priya (Creator), opened every screen and every tab,
and clicked every enabled button once per distinct label, plus the buttons inside any dialog or popover it opened
(only irreversible actions were skipped: delete, archive, sign out, empty the workspace). 375 clicks in total.

- It found one real bug: Content Auditor → Drafts and submissions → **Open** raised a Streamlit error. Fixed (the tab is
  now chosen before it is drawn) and re-checked for all three people.
- Two buttons (*Test in RuleProbe*, *Show in graph*) moved on screen during the crawl, so the crawler could not reach
  them; they were then checked directly for all three people and both open the right screen.
- After the fix: no exceptions and no JavaScript errors on any click.

### 4d · Public link mode (`BRANDCANON_PUBLIC=1`)

| Check | Result |
|---|---|
| Two visitors each receive a private 32-character token and their own copy of the demo | PASS |
| Visitor A empties its workspace; visitor B still sees all 21 approved rules | PASS |
| A page reload keeps visitor A's own copy (still empty) | PASS |

### 5 · Sign-in and Gemini status (two app instances, re-run after the final change)

All 12 checks passed, with no JavaScript errors:

| Check | Result |
|---|---|
| Sign-in page shown first, sidebar hidden | PASS |
| Wrong password rejected with a generic message | PASS |
| Signed in; sidebar shows *Deterministic logic* | PASS |
| Settings → AI and privacy shows provider; *Test Gemini connection* disabled when Gemini is off | PASS |
| Brand Manager adds a person with a password (Settings → Profile & people) | PASS |
| Deterministic audit labelled *Deterministic logic* | PASS |
| Deep link while signed out → sign-in page, then the requested page | PASS |
| Sign out returns to the sign-in page | PASS |
| Newly added person signs in | PASS |
| `AI_PROVIDER=gemini` with a fake key: the app checks the connection **by itself** at start-up and the sidebar shows *Gemini selected · connection failed* (no button pressed) | PASS |
| Audit with Gemini unreachable: red *Gemini did not produce this result … network error*; deterministic findings still shown and labelled | PASS |
| *Test Gemini connection* reports *Connection failed (network)*; the key string is absent from the whole page | PASS |

### 6 · Real SDK failure path

The real `google-genai` 3.0.0 SDK was called with a fake key from the build environment, where the proxy blocks Google:

- `check_connection()` returned `ok: False`, kind `network`, detail `ProxyError: 403 Forbidden`, with no key in the output.
- `python scripts/check_gemini.py` printed the same failure and exited with code 2.

With no provider configured it printed "Not checking … AI_PROVIDER is not gemini" and exited with code 1.

### 7 · Live smoke tests

- **On the team's MacBook with a real key (10 Nov 2026): 4 passed in 38.9 s** (`pytest -m live`, Python 3.14.10), after
  `python scripts/check_gemini.py` reported *"OK — Gemini (gemini-3.5-flash-lite) answered in 1622 ms"*. Screenshot:
  `docs/screenshots/09_live_gemini_verified.png`.
- Without a key, all 4 tests in `tests/test_live_gemini.py` are skipped with the reason shown.
- With `AI_PROVIDER=gemini` and a fake key, they run and fail with "Could not reach the Gemini API", because the network is
  blocked here. This shows they cannot pass without a real response.

## Accuracy on the labelled set (Settings → Accuracy)

| Task | Items | Precision | Recall | F1 |
|---|---|---|---|---|
| Ambiguity detection | 20 | 1.00 | 0.80 | 0.89 |
| Conflict detection | 10 | 0.80 | 0.67 | 0.73 |
| Claim checking | 20 | 1.00 | 1.00 | 1.00 |

Recomputed after the final change; unchanged. The set is small, was written by the team, and is for a fictional brand. The misses are listed in the app.

## Not tested
- **Live Gemini prompt quality at scale:** live Gemini was verified with the 4 smoke tests on the team's machine; the full
  NovaTech browser scenario was run with deterministic logic, not with live Gemini.
- **Load and concurrency:** multiple simultaneous users were not tested.
- **Visual audit on real creatives:** tested only with generated images.
- **Screen readers and mobile layouts:** contrast was checked against WCAG AA and the sign-in page was viewed at phone width, but
  no screen reader was used and the workspace screens are designed for desktop (the knowledge graph is mouse-driven).
- **User testing:** no sessions with real marketing teams have been run yet (planned for Round 2 in the Round 1 document).
