# User guide

BrandCanon is a **manually managed, document-based** brand-governance workspace. You upload PDF and DOCX documents;
BrandCanon extracts candidate rules and facts with their page references; people review them; only approved knowledge
is used to audit content. It does not fetch web pages or research companies on its own.

## The workspace
- **Sign in** first: choose the brand workspace and your name, then enter your password. In the fictional demo
  workspace every person uses `novatech-demo`. **Create a workspace** on the sign-in page makes you its Brand Manager.
- **Top bar:** the BrandCanon logo, the **workspace selector** (choosing another workspace takes you to its sign-in),
  **global search** (type and press Enter — searches rules, documents and passages, product facts, audit findings,
  decisions and content), **notifications** (what needs your attention, from real records) and your **profile menu**
  (Profile, Settings, Sign out).
- **Left sidebar** (collapsible with «; the » button brings it back and the workspace then uses the full width): Overview,
  Brand Constitution, RuleProbe, Content Auditor, Decision Memory, Governance Intelligence, Knowledge Graph, Settings and
  Help; at its foot, who is signed in and which AI engine is active.
- In split workspaces (RuleProbe, Decision Memory) the side panels stay in view as you scroll the middle column.
- Light screens use a sage frame and white cards; RuleProbe and the Knowledge Graph use the dark investigation design.
  Entity colours are the same everywhere: documents pink, rules turquoise, test cases yellow, findings coral,
  decisions lavender, products and campaigns mint.

| Role | Can do |
|---|---|
| **Brand Manager** | Upload documents; add, approve, edit, reject or archive documents, rules and facts; resolve conflicts; approve RuleProbe interpretations and update rules after authorisation; decide escalated content; manage people |
| **Reviewer** | Run RuleProbe, mark test outcomes, save investigations and send them for human review; approve, request changes, reject or escalate content; override findings and earlier decisions with a reason |
| **Creator** | Audit content, accept/edit/dismiss suggestions, re-run audits, submit for approval |

## Guided demo (NovaTech workspace only)
On the Overview, **Start** runs the guided demo on the current records; **Start from empty…** (Brand Manager, asks to
confirm) empties the fictional demo workspace first. A forest-green stepper above every screen shows six steps —
Upload, Conflict, Test rule, Audit, Approve, Insight — with the current one in yellow. **Take me there** opens the right
screen at the right record; when a step belongs to another person, **Sign in as …** signs out and pre-selects them. A step
is ticked only when the stored records show it done. **End guided demo** hides the stepper.

## Brand Intelligence Overview
Four metric cards counted from the database — **Approved brand rules**, **Pending reviews** (rules unreviewed, flagged
or with an open RuleProbe finding — the same rules Brand Constitution lists under *Needs review*), **Completed content
audits** and **Unresolved conflicts** — each opening the filtered page. Below: **Brand health** (rules by review status,
sources, facts and the Documents → Rules → Tests → Findings → Decisions chain, with a link to the Knowledge Graph),
**Governance trends** (first-draft findings per week by root cause, with the total, latest week and peak week), **Recent investigations**, **Content audit
activity** (issue distribution and categories), **Recent decisions** and **Areas requiring attention** (unresolved
conflicts, rules awaiting review, content awaiting approval, recurring problems), each item opening its record.

## Brand Constitution — your organisation's approved brand knowledge
- **Top actions:** *Search knowledge* (searches every stored source), *Add brand rule* (Brand Manager: the rule, its
  category, where it applies and why it is added; it is saved as Pending review unless you choose to approve it now; its
  source is shown as "added manually") and *Upload documents* (PDF or DOCX; choose a source authority or let BrandCanon
  detect it; optionally store as a new version of an existing document).
- **Document library:** a card per document with file type, version, upload date, review status, number of extracted
  rules and authority. **All knowledge** shows everything.
- **Knowledge categories:** brand voice, tone and personality, terminology, messaging, product facts, approved claims,
  restricted claims, visual identity, accessibility, campaign instructions — each with a live count, used as a filter.
- **Split workspace** when a document is opened: **left** the document information, review actions (approve or reject as
  a source, archive, delete — destructive actions ask for confirmation), a **preview of its stored pages** and version
  comparison; **centre** the extracted rules (search, status filter, *Approve pending* by authority); **right** the
  selected rule's source details — evidence trail, supporting passage (or "Source reference unavailable"), *View source
  page* — and **Approve, Edit (new version), Reject, Archive**, *Test in RuleProbe* and *Show in graph*.
- **Product facts** and **Terminology** tabs hold numeric specifications (with qualifiers) and banned/preferred terms.
  Approving a document never approves its rules; extracted knowledge is never treated as approved automatically.

## RuleProbe — test the logic behind your brand guidelines (dark workspace)
- **Left:** search rules, filter by **category**, **approval status** and **investigation type** (ambiguity,
  contradiction, missing guidance, model uncertainty, no issue found, not tested), choose the rule (◆ marks an earlier
  potential finding), see related rules.
- **Centre:** the rule; context and product; **test cases** — each generated example changes one characteristic; edit
  any example, remove it, **Add manual case** or **Generate test cases** again. **Execute tests** judges every example
  under a strict and a lenient reading. Results: the divergence gauge (with the 20 % limit), one column per example with
  both readings, and a coloured outcome dot — **green** likely compliant, **red** potential violation, **yellow**
  uncertain, **pink** needs human review. Then the **investigation map** — brand rule → test cases → findings → source
  documents — where clicking a node opens its record, and *Explanations and reviewer marks*.
- **Right:** investigation details — selected rule, source document, the potential finding with its explanation,
  related rules and conflicts, relevant cases, supporting source, reasoning and reviewer status, and the timeline.
- **Actions:** *Save investigation*, *Send for human review* (with a note), *Approve interpretation* and *Update rule
  after authorisation* (Brand Manager; saves a new version and shows the diff). A test never changes a rule by itself.
- **Conflicts** (choose the source of truth, narrow a scope, archive one rule or confirm both can coexist), **Missing
  guidance** and **Test history** (divergence before and after clarification).

## Content Intelligence (Content Auditor) — examine content before it reaches your audience
- **Left — editor:** title, content type, channel, product, campaign and the content itself; or **load the text from a
  PDF or DOCX**. **Submit for audit**. After auditing: the marked-up text, *Edit manually*, **Re-run audit**, **Submit
  for approval**, **Save report**, the first draft → current revision panel, revision comparison and comments.
- **Right — findings:** summary metrics and the finding types present (tone mismatch, terminology violation, messaging
  inconsistency, contradicted / unsupported / unverifiable claims, accessibility). Each finding is a card;
  **Examine finding** highlights its phrase in the text and opens the explanation, the evidence trail, the related
  approved rule, the supporting passage and *View source page*, any precedent, and the **suggested correction** with
  **Accept suggestion**, **Edit manually** and **Dismiss finding** (with a reason, carried to later revisions).
  **Accept all** applies every suggested correction as one new revision.
- *Contradicted* = evidence conflicts with the claim; *Unsupported* = no sufficient approved evidence; *Unverifiable* =
  the information cannot settle it. Nothing is called false without conflicting evidence.
- When a similar claim was decided before: "An earlier review addressed a similar claim. View previous decision."

## Decision Memory — remember the reasoning behind every authorised decision
- **Review queue:** compare revisions, see findings with evidence and precedents, override a finding with a reason,
  comment, then approve, request changes, reject or escalate (a rationale is required; escalated items need a Brand
  Manager).
- **Decision history:** filters on the left (content phrase, rule, product, campaign, reviewer, date, decision status);
  decision cards in the centre (original content, finding, decision, reasoning, rule, source document and version,
  reviewer, time); the selected decision in a dark detail panel on the right (reasoning, evidence trail, supporting
  source, original vs corrected content, approval status and full review history). Stale precedents are flagged;
  overriding keeps the earlier decision in history but stops offering it as precedent. A decision never becomes a rule.
- **Approval history:** a timeline per submission.

## Governance Intelligence — discover patterns behind recurring brand inconsistencies
Four metrics (recurring violations, unresolved ambiguities, source conflicts, **average review time** with its median),
**Where to act** (fix the people, the rules or the documents), then the charts — each headed by the figures that matter
(total, weekly average, peak week, approval rate) computed from the same records:
- **Findings over time:** weekly columns with the week's total on top and the week's start date under it; switch the
  breakdown between *Classification*, *Root cause* and *Severity*.
- **Issue categories** and **Root cause analysis:** ranked bars labelled with count and share.
- **Findings by channel:** which channels produce findings, split by severity.
- **Most frequently violated rules**, **terminology issues** and **repeated unsupported claims:** ranked lists with
  proportional bars; hover a row for the full text.
- **Reviewer decision trends:** decisions per week, with the overall approval rate and revisions before approval.
- **Unresolved ambiguities** (with each rule's divergence) and **recommended actions**, each with a button to act.

Chart colours are deeper, validated steps of the brand hues (checked for colour-blind and normal-vision separation),
and every chart also labels its values, so colour is never the only cue.

## Brand Knowledge Graph (dark workspace)
Every stored document, rule, test case, finding, decision and product/campaign as a node; every edge is a stored
relationship (document contains rule, rule tested by test case, test case produces finding, finding contradicts or
concerns a rule, finding supported by a document, finding resolved through a decision, decision applies to rule, about
a product or campaign). Search, entity and relationship filters, four layouts (force-directed, circular, hierarchical,
grid), labels, **Focus on selection**, a legend, zoom (scroll or + / −), pan (drag) and reset (double-click). **Click a
node** to see its stored fields and connections in the details panel, then open it in its own screen. Nodes grow with
the number of records they connect to, and the tooltip gives the connection count. Before anything is selected, the
details panel summarises the view: records per type and the most connected records.

## Every result says where it came from
*Live Gemini* (validated response; *cached* when reused), *Deterministic logic*, *Demo fallback* (the pre-built demo
history), or *Gemini failed* (a red message says what failed; deterministic checks ran instead).

## Settings and Help
- **Settings:** profile and people (add people, reset and change passwords), AI and privacy (provider, model, whether
  a key is configured — never the key — *Test Gemini connection*), accuracy on the labelled set, recorded test results,
  demo reset.
- **Help & documentation:** a glossary of every finding type and these guides.
