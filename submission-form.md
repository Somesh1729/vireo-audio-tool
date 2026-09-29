# Submission Form — Vireo Audio Support Tickets

**Candidate:** Somesh Yallapur
**Date submitted:** 30/09/2026
**Time spent:** 3 hours

## 1. The tool

`run_report.py` — reads tickets.csv + agent.csv, applies the
first-response SLA rules from support-policy.pdf §3, and outputs a
weekly breach report in two views: by the shift window a ticket was
created in (structural, no agent identity needed) and by resolving
agent (individual, restricted to tickets with no hand-offs, where
attribution is reliable).

Runs from a clean machine with:
    pip install -r requirements.txt
    python run_report.py --data ./data --out ./output

Full instructions in README.md.

## 2. Business goal, as a number

First-response SLA breach rate roughly tripled from ~9% (Jan–Jun
2025) to ~25% (Jul 2025 onward) and has stayed there for a year.
Traced to the elimination of the Indore Night shift on 30 June 2025
— overnight chat breach rate went from 7.8% to 99.9%.

**Goal: bring the breach rate back from ~25% toward the ~9%
pre-July-2025 baseline, worth approximately Rs 150,000/quarter in
SLA credits alone** (Rs 350 × incremental monthly breaches × 3),
not counting repeat-contact cost or CSAT impact. Overnight chat
alone accounts for ~46% of all breaches since July 2025 and ~Rs
87,000/quarter of that figure — the most concentrated, most
fixable piece.

## 3. Evidence the tool is correct

`validate.py` runs two kinds of check:
- An independent recompute of the breach flag on a random 50-ticket
  sample, using a separate implementation with no shared code —
  100% agreement.
- Three targeted edge-case tests: point-in-time roster join across
  an agent's shift change, midnight-crossing shift boundary
  classification, and dedup row-count correctness.

All four checks currently pass. One of the edge-case tests (the
roster-join check) caught a real bug during development — an
earlier version of the join silently misassigned shifts for agents
who moved shifts, via a pandas reindex-after-merge issue. Fixed and
re-verified; see DECISIONS.md #12.

## 4. Memo

`memo_to_neha.md` — one page, non-technical, leads with the finding
(coverage gap, not agent performance) and the Rs figure.

## 5. Screen recording

`recording.mp4` (≤3 min) — prompts used, what changed between
versions (the roster-join bug fix), what was discarded (the
optional LLM/free-text classification step; attributing breaches to
the resolving agent regardless of hand-offs), and a live run.

## 6. AI tool usage disclosure

**What I used:** [Claude], for: exploratory data analysis guidance, drafting
and debugging run_report.py/validate.py/make_charts.py, and
drafting this memo and documentation.

**What I discarded:**
- An LLM-based classification of breached tickets' closing notes
  into "legitimate reason" vs. "true miss" — scoped but not built;
  the structural finding already explains most of the increase
  without it, and building it risked eating the time budget without
  materially changing the recommendation.
- Attributing every breach to the resolving agent regardless of
  ticket hand-offs (matches the policy's own stated convention, §3)
  — rejected because it risks blaming individuals for delays caused
  upstream, which is exactly what Priya's email asked not to happen.
- An initial version of the roster join, replaced after validate.py
  caught it producing wrong shift assignments for agents who moved
  shifts (see DECISIONS.md #12).

## 7. What was left out of scope, and why

- No AI/LLM component in the core pipeline — breach determination
  needs to be exact and auditable, not probabilistic (see
  DECISIONS.md #10).
- Tier 2 (Escalations & Warranty) tickets are not compared to Tier 1
  in the weekly breach report — the policy itself (§6) says Tier 2
  isn't measured on the same volume metrics.
- Sameer's claim of "~40 failed IVR transcripts" was checked against
  the data (only ~2 clearly garbage rows found) and flagged rather
  than acted on, since there was no reliable basis to exclude
  specific rows (DECISIONS.md #9).