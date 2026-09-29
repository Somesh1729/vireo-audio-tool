# Vireo Audio — Weekly SLA Breach Report Tool

A small tool that reads Vireo's support ticket export and roster, and
produces a weekly first-response SLA breach report by agent and by
shift, per support-policy.pdf v3.2.

## Setup

Requires Python 3.9+.

    pip install -r requirements.txt

## Data

Place these five files, unchanged, in `./data/`:
- tickets.csv
- agent.csv        (the pack's own README calls this agents.csv — renamed here; see DECISIONS.md)
- orders.csv
- customers.csv
- products.csv

## Run

    python run_report.py --data ./data --out ./output
    python validate.py   --data ./data --out ./output
    python make_charts.py --out ./output

## Output (in ./output/)

- `weekly_breach_by_shift.csv` — structural view: breach rate by the
  shift window a ticket was CREATED in. No agent identity involved.
- `weekly_breach_by_agent.csv` — individual view: breach rate by the
  RESOLVING agent, restricted to tickets with no hand-offs
  (transfers == 0), weeks under 5 tickets suppressed.
- `overnight_chat_spillover_detail.csv` — every chat ticket created
  22:00–06:00 IST, isolated for inspection.
- `tickets_enriched.csv` — the full ticket set with every derived
  column (breach flag, shift, dedup applied), for anyone who wants
  to check the work directly.
- `chart_monthly_breach_rate.png`, `chart_overnight_vs_daytime_chat.png`

`validate.py` prints a pass/fail summary to the console — an
independent recompute on a random sample plus three edge-case checks
(roster boundary, shift-hour boundary, dedup row count). All four
currently pass.

## What this does NOT do

No LLM/AI step. The free-text fields (customer_message, agent_notes)
were reviewed but not used — see DECISIONS.md for why, and what an
AI-assisted extension would look like if scope allowed.

## Known data quirk

The pack's own README (`data/README.txt`, if you kept it) names the
roster file `agents.csv`; the actual uploaded file is `agent.csv`
(singular). The code reads `agent.csv` — rename the file or the
`load_agents()` line if your copy is named differently.