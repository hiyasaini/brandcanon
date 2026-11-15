"""Governance Intelligence: aggregates computed only from stored records. Nothing here is hardcoded."""
from collections import Counter, defaultdict
from datetime import datetime

from database import db, repositories as repo
from modules import conflict_detection

ISSUE = lambda f: f["classification"] != "Verified"  # noqa: E731


def _week(ts):
    return datetime.fromisoformat(ts[:19]).strftime("%G-W%V")


def summary(ws, date_from=None, date_to=None, channel=None):
    rows = repo.findings_for_analytics(ws, date_from, date_to, channel)
    issues = [f for f in rows if ISSUE(f)]
    first = [f for f in issues if f["revision_no"] == 1]
    subs = repo.list_submissions(ws)
    # latest report per submission -> unresolved = open issues on content that is not approved/rejected
    latest_rev = {}
    for f in issues:
        key = f["submission_id"]
        latest_rev[key] = max(latest_rev.get(key, 0), f["revision_no"])
    unresolved = [f for f in issues if f["revision_no"] == latest_rev[f["submission_id"]] and f["disposition"] == "open"
                  and f["submission_status"] not in ("Approved", "Rejected")]
    reports = db.fetch_one("SELECT COUNT(*) n FROM audit_reports WHERE workspace_id = ?" +
                           (" AND created_at >= ?" if date_from else "") + (" AND created_at <= ?" if date_to else ""),
                           tuple([ws] + ([date_from] if date_from else []) + ([date_to + "T23:59:59"] if date_to else [])))["n"]
    tests = repo.all_tests(ws)
    amb_by_rule = Counter(t["code"] for t in tests if t["classification"] == "Ambiguous rule")
    approvals = db.fetch_all("""SELECT a.outcome, a.created_at FROM approvals a JOIN content_submissions s ON s.id = a.submission_id
                                WHERE s.workspace_id = ? ORDER BY a.created_at""", (ws,))
    weekly_root = defaultdict(Counter)
    for f in first:
        weekly_root[_week(f["report_at"])][f["root_cause"]] += 1
    weekly_appr = defaultdict(Counter)
    for a in approvals:
        weekly_appr[_week(a["created_at"])][a["outcome"]] += 1
    weekly_amb = defaultdict(int)
    for t in tests:
        if t["classification"] == "Ambiguous rule":
            weekly_amb[_week(t["created_at"])] += 1
    revs = db.fetch_all("""SELECT s.id, MAX(r.revision_no) n FROM content_submissions s JOIN content_revisions r ON r.submission_id = s.id
                           WHERE s.workspace_id = ? AND s.status = 'Approved' GROUP BY s.id""", (ws,))
    return {
        "n_reports": reports,
        "n_submissions": len(subs),
        "status_counts": Counter(s["status"] for s in subs),
        "n_issues_first": len(first),
        "n_unresolved": len(unresolved),
        "root_causes": Counter(f["root_cause"] for f in first),
        "categories": Counter(f["category"] for f in first),
        "classifications": Counter(f["classification"] for f in first),
        "terminology": Counter(f["quote"].lower() for f in first if f["category"] == "Terminology" and f["quote"]),
        "claims": Counter(f["quote"] for f in first if f["category"] in ("Claims", "Product facts") and f["quote"]),
        "rules_broken": Counter(f["rule_code"] for f in first if f["rule_code"]),
        "ambiguous_rules": amb_by_rule,
        "open_conflicts": repo.list_conflicts(ws, "open"),
        "weekly_root": dict(sorted(weekly_root.items())),
        "weekly_approvals": dict(sorted(weekly_appr.items())),
        "weekly_ambiguity": dict(sorted(weekly_amb.items())),
        "avg_revisions_to_approval": round(sum(r["n"] for r in revs) / len(revs), 2) if revs else None,
        "first_findings": first,
        "unresolved": unresolved,
    }


def recommendations(ws, S):
    """Actionable suggestions, each tied to the records that justify it."""
    recs = []
    rc = S["root_causes"]
    if S["open_conflicts"]:
        recs.append({"title": "Resolve conflicting source documents", "root_cause": "Source conflict",
                     "detail": f"{len(S['open_conflicts'])} conflict(s) are still open; {rc.get('Source conflict', 0)} finding(s) trace back to them.",
                     "evidence": [c["title"] for c in S["open_conflicts"][:5]]})
    elif rc.get("Source conflict"):
        recs.append({"title": "Update product specifications", "root_cause": "Source conflict",
                     "detail": f"{rc['Source conflict']} finding(s) used figures from lower-authority or outdated documents. Retire or correct "
                               "them so the specification is the only figure in circulation.",
                     "evidence": [q for q, _ in S["claims"].most_common(3)]})
    from modules import rule_probe
    open_amb = [x["rule"] for x in rule_probe.open_findings(ws) if x["test"]["classification"] == "Ambiguous rule"]
    hist_amb = S["ambiguous_rules"]
    if open_amb or rc.get("Guideline defect") or hist_amb:
        resolved = len(set(hist_amb) - {r["code"] for r in open_amb})
        recs.append({"title": "Clarify a guideline", "root_cause": "Guideline defect",
                     "detail": f"RuleProbe found {len(hist_amb)} ambiguous rule(s) ({resolved} clarified, {len(open_amb)} still open); "
                               f"{rc.get('Guideline defect', 0)} finding(s) depended on an unclear rule.",
                     "evidence": [f"{r['code']}: {r['text'][:70]}" for r in open_amb[:5]] or [f"{k} (clarified)" for k in hist_amb][:5]})
    gaps = conflict_detection.coverage_gaps(ws)
    if rc.get("Knowledge gap") or gaps:
        recs.append({"title": "Improve missing documentation", "root_cause": "Knowledge gap",
                     "detail": f"{rc.get('Knowledge gap', 0)} finding(s) had no approved evidence or policy; {len(gaps)} channel(s) have no specific rules.",
                     "evidence": gaps[:6]})
    if rc.get("Creator error"):
        top = S["categories"].most_common(2)
        recs.append({"title": "Provide creator training", "root_cause": "Creator error",
                     "detail": f"{rc['Creator error']} finding(s) broke clear rules. Most common: " + ", ".join(f"{k} ({v})" for k, v in top) + ".",
                     "evidence": [f"{k} × {v}" for k, v in S["rules_broken"].most_common(4)]})
    stale_docs = db.fetch_all("""SELECT d.title, v.version_label, v.effective_date FROM documents d
                                 JOIN document_versions v ON v.document_id = d.id AND v.is_current = 1
                                 WHERE d.workspace_id = ? AND d.status = 'active' AND d.authority_rank <= 1""", (ws,))
    if stale_docs:
        recs.append({"title": "Review low-authority documents", "root_cause": "Source conflict",
                     "detail": "These documents rank lowest in authority but are still active; archive or update them.",
                     "evidence": [f"{d['title']} v{d['version_label']}" for d in stale_docs]})
    return recs


def recurring_violations(S, min_count=2):
    """Issues that recur across different pieces of content (first drafts), grouped by rule, banned term or claim type."""
    groups, labels = defaultdict(set), {}
    for f in S["first_findings"]:
        if f["rule_code"]:
            key = ("rule", f["rule_code"])
            labels[key] = f"{f['rule_code']} · {f['category'].lower()}"
        elif f["category"] == "Terminology" and f["quote"]:
            key = ("term", f["quote"].lower())
            labels[key] = f"Banned term “{f['quote']}”"
        else:
            key = ("type", f"{f['classification']} · {f['category']}")
            labels[key] = f"{f['classification']} {f['category'].lower()} claims"
        groups[key].add(f["submission_id"])
    out = [{"kind": k[0], "key": k[1], "label": labels[k], "count": len(v), "submissions": sorted(v)}
           for k, v in groups.items() if len(v) >= min_count]
    return sorted(out, key=lambda x: -x["count"])


def review_turnaround(ws):
    """Hours from the revision a reviewer decided on to the decision, for every recorded decision. Returns (median, n)."""
    rows = db.fetch_all("""SELECT a.created_at decided, r.created_at revised FROM approvals a
                           JOIN content_revisions r ON r.id = a.revision_id
                           JOIN content_submissions s ON s.id = a.submission_id WHERE s.workspace_id = ?""", (ws,))
    hours = sorted(max(0.0, (datetime.fromisoformat(x["decided"][:19]) - datetime.fromisoformat(x["revised"][:19])).total_seconds() / 3600)
                   for x in rows)
    if not hours:
        return None, 0
    m = len(hours) // 2
    median = hours[m] if len(hours) % 2 else (hours[m - 1] + hours[m]) / 2
    return round(median, 2), len(hours)



def review_time_stats(ws):
    """Average (mean) and median hours from the reviewed revision to the decision. Returns (mean, median, n)."""
    median, n = review_turnaround(ws)
    if not n:
        return None, None, 0
    rows = db.fetch_all("""SELECT a.created_at decided, r.created_at revised FROM approvals a
                           JOIN content_revisions r ON r.id = a.revision_id
                           JOIN content_submissions s ON s.id = a.submission_id WHERE s.workspace_id = ?""", (ws,))
    hours = [max(0.0, (datetime.fromisoformat(x["decided"][:19]) - datetime.fromisoformat(x["revised"][:19])).total_seconds() / 3600)
             for x in rows]
    return round(sum(hours) / len(hours), 2), median, n


def repeated_unsupported_claims(S):
    """Claims flagged as unsupported or unverifiable more than once (first drafts), most frequent first."""
    cnt = Counter(f["quote"] for f in S["first_findings"] if f["classification"] in ("Unsupported", "Unverifiable") and f["quote"])
    return [(k, v) for k, v in cnt.most_common() if v >= 2] or cnt.most_common(5)
