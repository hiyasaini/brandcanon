"""Brand Knowledge Graph — nodes and relationships built only from stored records, plus layout algorithms.

Nodes: documents, brand rules, RuleProbe test cases, findings (RuleProbe investigation findings and audit findings),
reviewer decisions, products and campaigns. Every edge corresponds to a stored foreign key or stored list:

  Document  —contains→        Rule        (brand_rules.version_id → document)
  Rule      —tested by→       Test case   (latest rule_tests run for the rule → rule_test_cases)
  Test case —produces→        Finding     (cases whose strict and lenient readings split, in a test with a finding)
  Finding   —contradicts→     Rule        (rule_tests.related_rule_ids of a contradiction finding)
  Finding   —concerns→        Rule        (audit_findings.rule_id)
  Finding   —supported by→    Document    (audit_findings.passage_id → passage → document)
  Finding   —resolved through→ Decision   (decisions.finding_id, or the submission's outcome decision)
  Decision  —applies to→      Rule        (decisions.rule_id)
  Finding / Decision —about→  Product or campaign (stored product / campaign fields)

Nothing is generated, sampled or invented. The UI renders whatever this returns.
"""
import json
import math
import random
from collections import defaultdict

from database import db

RELATIONS = {
    "contains": "Document contains rule",
    "tested_by": "Rule tested by test case",
    "produces": "Test case produces finding",
    "contradicts": "Finding contradicts rule",
    "concerns": "Finding concerns rule",
    "supported_by": "Finding supported by evidence",
    "resolved_through": "Finding resolved through decision",
    "applies_to": "Decision applies to rule",
    "about": "About product / campaign",
}
KINDS = ("document", "rule", "case", "finding", "decision", "product")
OUTCOME_DECISIONS = ("Approved", "Changes requested", "Rejected", "Escalated")


def build(ws):
    nodes, edges = {}, []

    def add(nid, kind, label, detail, open_=None, extra=None):
        nodes[nid] = {"id": nid, "kind": kind, "label": label, "detail": detail, "open": open_ or [], **(extra or {})}

    def link(a, b, rel):
        if a in nodes and b in nodes and a != b:
            edges.append({"source": a, "target": b, "rel": rel})

    # documents
    for d in db.fetch_all("""SELECT d.*, v.version_label, v.file_name,
                             (SELECT COUNT(*) FROM brand_rules r JOIN document_versions v2 ON v2.id = r.version_id
                              WHERE v2.document_id = d.id AND r.status NOT IN ('Archived', 'Superseded')) n_rules
                             FROM documents d LEFT JOIN document_versions v ON v.document_id = d.id AND v.is_current = 1
                             WHERE d.workspace_id = ? AND d.status = 'active'""", (ws,)):
        add(f"doc:{d['id']}", "document", d["title"],
            {"Type": "Document", "Title": d["title"], "Version": d["version_label"] or "—", "File": d["file_name"] or "—",
             "Authority": f"{d['authority_level']} · {d['authority_rank']}/5", "Review status": d["review_status"],
             "Rules extracted": d["n_rules"]},
            [("Open in Brand Constitution", "constitution", {"con_doc": d["id"]})])

    # rules
    for r in db.fetch_all("""SELECT r.*, v.document_id, p.location FROM brand_rules r
                             LEFT JOIN document_versions v ON v.id = r.version_id LEFT JOIN passages p ON p.id = r.passage_id
                             WHERE r.workspace_id = ? AND r.status NOT IN ('Archived', 'Superseded', 'Rejected')""", (ws,)):
        add(f"rule:{r['id']}", "rule", r["code"],
            {"Type": "Brand rule", "Rule": f"{r['code']} v{r['rule_version']}", "Text": r["text"], "Category": r["category"],
             "Status": r["status"], "Clarity": r["clarity"],
             "Source page": r["location"] or "Source reference unavailable"},
            [("Open rule in Brand Constitution", "constitution", {"con_rule": r["id"]}),
             ("Investigate in RuleProbe", "ruleprobe", {"probe_rule": r["id"]})])
        if r["document_id"]:
            link(f"doc:{r['document_id']}", f"rule:{r['id']}", "contains")

    # latest RuleProbe test per rule → cases → investigation finding
    tests = db.fetch_all("""SELECT t.*, r.code FROM rule_tests t JOIN brand_rules r ON r.id = t.rule_id
                            WHERE r.workspace_id = ? AND t.id IN (SELECT MAX(id) FROM rule_tests GROUP BY rule_id)""", (ws,))
    for t in tests:
        rid = f"rule:{t['rule_id']}"
        if rid not in nodes:
            continue
        inv = None
        if t["classification"] != "Clear rule":
            inv = f"inv:{t['id']}"
            add(inv, "finding", f"{t['code']} · {t['classification']}",
                {"Type": "RuleProbe finding", "Finding": f"Potential {t['classification'].lower()}", "Rule": t["code"],
                 "Divergence": f"{t['divergence']:.0%}", "Issue": t["issue"], "Investigation": t["investigation_state"],
                 "Run on": t["created_at"][:10]},
                [("Open investigation in RuleProbe", "ruleprobe", {"probe_rule": t["rule_id"]})], {"sub": "investigation"})
            for other in json.loads(t["related_rule_ids"] or "[]"):
                if t["classification"] == "Contradictory rules":
                    link(inv, f"rule:{other}", "contradicts")
        cases = db.fetch_all("SELECT * FROM rule_test_cases WHERE test_id = ? ORDER BY seq", (t["id"],))
        for n_, cs in enumerate(cases, 1):
            cid = f"case:{cs['id']}"
            add(cid, "case", f"#{n_}",
                {"Type": "Test case", "Rule": t["code"], "Example": cs["example"],
                 "Changes": "baseline" if cs["dimension"] == "baseline" else f"{cs['dimension']} · level {cs['level']}",
                 "Strict reading": cs["strict_verdict"], "Lenient reading": cs["lenient_verdict"],
                 "Outcome": cs["assessment"], "Reviewer mark": cs["reviewer_mark"] or "—"},
                [("Open test in RuleProbe", "ruleprobe", {"probe_rule": t["rule_id"]})])
            link(rid, cid, "tested_by")
            if inv and cs["strict_verdict"] != cs["lenient_verdict"]:
                link(cid, inv, "produces")
        if inv and not any(e["target"] == inv and e["rel"] == "produces" for e in edges):
            for cs in cases:   # no split case (e.g. a contradiction): the finding comes from the whole test run
                if cs["assessment"] != "Likely compliant":
                    link(f"case:{cs['id']}", inv, "produces")

    # audit findings (one node per distinct issue in a piece of content; later revisions of the same issue map to it)
    rows = db.fetch_all("""SELECT f.*, s.id submission_id, s.title sub_title, s.product, s.campaign, cr.revision_no,
                           v.document_id evidence_doc FROM audit_findings f
                           JOIN audit_reports a ON a.id = f.report_id JOIN content_revisions cr ON cr.id = a.revision_id
                           JOIN content_submissions s ON s.id = cr.submission_id
                           LEFT JOIN passages p ON p.id = f.passage_id LEFT JOIN document_versions v ON v.id = p.version_id
                           WHERE a.workspace_id = ? AND f.classification != 'Verified' ORDER BY f.id""", (ws,))
    node_of, by_sub = {}, defaultdict(list)
    for f in rows:
        key = f"af:{f['submission_id']}:{(f['quote'] or '').lower()}:{f['classification']}"
        if key not in nodes:
            add(key, "finding", f"“{(f['quote'] or 'whole text')[:28]}”",
                {"Type": "Audit finding", "Phrase": f"“{f['quote'] or 'whole text'}”", "Classification": f["classification"],
                 "Severity": f["severity"], "Category": f["category"], "Explanation": f["message"], "Root cause": f["root_cause"],
                 "Evidence": f["evidence_source"] or "No approved evidence", "Content": f["sub_title"],
                 "First seen": f"revision {f['revision_no']}", "Status": f["disposition"]},
                [("Open in Content Auditor", "auditor", {"aud_sub": f["submission_id"]})], {"sub": "audit"})
            by_sub[f["submission_id"]].append(key)
            if f["rule_id"]:
                link(key, f"rule:{f['rule_id']}", "concerns")
            if f["evidence_doc"]:
                link(key, f"doc:{f['evidence_doc']}", "supported_by")
            for name, pref in ((f["product"], "prod"), (f["campaign"], "camp")):
                if name:
                    pid = f"{pref}:{name}"
                    if pid not in nodes:
                        add(pid, "product", name, {"Type": "Product" if pref == "prod" else "Campaign", "Name": name},
                            [("Search this name", "search", {"search_q": name})])
                    link(key, pid, "about")
        node_of[f["id"]] = key

    # decisions
    decs = db.fetch_all("""SELECT d.*, u.name reviewer, s.title sub_title FROM decisions d LEFT JOIN users u ON u.id = d.reviewer_id
                           LEFT JOIN content_submissions s ON s.id = d.submission_id WHERE d.workspace_id = ? ORDER BY d.id""", (ws,))
    latest_outcome = {}
    for d in decs:
        did = f"dec:{d['id']}"
        add(did, "decision", d["decision"],
            {"Type": "Reviewer decision", "Decision": d["decision"], "Claim": d["claim_text"] or "—",
             "Reasoning": d["explanation"], "Reviewer": d["reviewer"] or "—", "Content": d["sub_title"] or "—",
             "Date": d["created_at"][:10]},
            [("Open in Decision Memory", "decisions", {"dm_decision": d["id"]})])
        if d["rule_id"]:
            link(did, f"rule:{d['rule_id']}", "applies_to")
        if d["finding_id"] and d["finding_id"] in node_of:
            link(node_of[d["finding_id"]], did, "resolved_through")
        if d["decision"] in OUTCOME_DECISIONS and d["submission_id"]:
            latest_outcome[d["submission_id"]] = did
        if d["product"]:
            pid = f"prod:{d['product']}"
            if pid in nodes:
                link(did, pid, "about")
    for sid, did in latest_outcome.items():
        for key in by_sub.get(sid, []):
            if not any(e["source"] == key and e["rel"] == "resolved_through" for e in edges):
                link(key, did, "resolved_through")

    # de-duplicate edges
    seen, uniq = set(), []
    for e in edges:
        k = (e["source"], e["target"], e["rel"])
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return {"nodes": list(nodes.values()), "edges": uniq}


def subgraph(G, kinds=None, rels=None, focus=None, depth=1, query=""):
    """Filter by entity kinds and relationship types; optionally keep only the neighbourhood of `focus` or of nodes
    whose label/detail matches `query`. Returns a new graph dict."""
    kinds = set(kinds or KINDS)
    rels = set(rels or RELATIONS)
    nodes = {n["id"]: n for n in G["nodes"] if n["kind"] in kinds}
    edges = [e for e in G["edges"] if e["rel"] in rels and e["source"] in nodes and e["target"] in nodes]
    seeds = set()
    if focus and focus in nodes:
        seeds = {focus}
    elif query:
        ql = query.lower()
        seeds = {n["id"] for n in nodes.values() if ql in n["label"].lower()
                 or any(ql in str(v).lower() for v in n["detail"].values())}
    if seeds:
        keep = set(seeds)
        frontier = set(seeds)
        for _ in range(depth):
            nxt = set()
            for e in edges:
                if e["source"] in frontier:
                    nxt.add(e["target"])
                if e["target"] in frontier:
                    nxt.add(e["source"])
            frontier = nxt - keep
            keep |= nxt
        nodes = {k: v for k, v in nodes.items() if k in keep}
        edges = [e for e in edges if e["source"] in keep and e["target"] in keep]
    return {"nodes": list(nodes.values()), "edges": edges, "seeds": sorted(seeds)}


def neighbours(G, nid):
    out = []
    by_id = {n["id"]: n for n in G["nodes"]}
    for e in G["edges"]:
        if e["source"] == nid and e["target"] in by_id:
            out.append((RELATIONS[e["rel"]], "→", by_id[e["target"]]))
        elif e["target"] == nid and e["source"] in by_id:
            out.append((RELATIONS[e["rel"]], "←", by_id[e["source"]]))
    return out


# ------------------------------------------------------------------ layouts (deterministic, no extra dependencies)
LEVEL = {"document": 0, "rule": 1, "case": 2, "finding": 3, "decision": 4, "product": 5}


def layout(G, kind="force"):
    ids = [n["id"] for n in G["nodes"]]
    if not ids:
        return {}
    if kind == "circular":
        order = sorted(G["nodes"], key=lambda n: (LEVEL[n["kind"]], n["label"]))
        return {n["id"]: (math.cos(2 * math.pi * i / len(order)), math.sin(2 * math.pi * i / len(order)))
                for i, n in enumerate(order)}
    if kind == "grid":
        order = sorted(G["nodes"], key=lambda n: (LEVEL[n["kind"]], n["label"]))
        cols = max(1, math.ceil(math.sqrt(len(order) * 1.6)))
        return {n["id"]: (i % cols, -(i // cols)) for i, n in enumerate(order)}
    if kind == "hierarchical":
        rows = defaultdict(list)
        for n in sorted(G["nodes"], key=lambda n: n["label"]):
            rows[LEVEL[n["kind"]]].append(n["id"])
        pos = {}
        for lvl, row in rows.items():
            for i, nid in enumerate(row):
                pos[nid] = ((i + 0.5) / len(row), -lvl)
        return pos
    return _force(G)


def _force(G, iters=220, seed=7):
    """Fruchterman–Reingold spring layout with a fixed seed, so the same records always give the same picture."""
    rnd = random.Random(seed)
    ids = [n["id"] for n in G["nodes"]]
    n = len(ids)
    pos = {i: [rnd.uniform(-1, 1), rnd.uniform(-1, 1)] for i in ids}
    if n == 1:
        return {ids[0]: (0.0, 0.0)}
    k = math.sqrt(4.0 / n)
    t = 0.12
    adj = [(e["source"], e["target"]) for e in G["edges"]]
    for _ in range(iters):
        disp = {i: [0.0, 0.0] for i in ids}
        for a_i in range(n):
            a = ids[a_i]
            ax, ay = pos[a]
            for b_i in range(a_i + 1, n):
                b = ids[b_i]
                dx, dy = ax - pos[b][0], ay - pos[b][1]
                d2 = dx * dx + dy * dy or 1e-6
                f = k * k / d2
                disp[a][0] += dx * f
                disp[a][1] += dy * f
                disp[b][0] -= dx * f
                disp[b][1] -= dy * f
        for a, b in adj:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.sqrt(dx * dx + dy * dy) or 1e-6
            f = d / k
            disp[a][0] -= dx * f
            disp[a][1] -= dy * f
            disp[b][0] += dx * f
            disp[b][1] += dy * f
        for i in ids:  # gentle gravity keeps disconnected parts on screen
            disp[i][0] -= pos[i][0] * 0.6
            disp[i][1] -= pos[i][1] * 0.6
            dx, dy = disp[i]
            d = math.sqrt(dx * dx + dy * dy) or 1e-6
            pos[i][0] += dx / d * min(d, t)
            pos[i][1] += dy / d * min(d, t)
        t *= 0.985
    return {i: (p[0], p[1]) for i, p in pos.items()}
