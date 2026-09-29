import argparse
from pathlib import Path
import pandas as pd

SLA_TARGET_MIN = {"chat": 15, "voice": 120, "social": 240, "email": 480}
BREACH_CREDIT_INR = 350


def _shift_for_hour(h: int) -> str:
    if 6 <= h < 14:
        return "Morning"
    if 14 <= h < 22:
        return "Day"
    return "Night"


def load_tickets(data_dir: Path) -> pd.DataFrame:
    t = pd.read_csv(data_dir / "tickets.csv")
    for c in ["created_at", "first_response_at", "resolved_at"]:
        t[c] = pd.to_datetime(t[c], errors="coerce")

    # Decision 1: dedup migration re-import pairs. Every duplicated
    # ticket_id is exactly one 'helpdesk' + one 'legacy_fd' row,
    # identical except csat_score. Keep the helpdesk row.
    dup_ids = t.ticket_id[t.ticket_id.duplicated(keep=False)]
    drop_idx = t[(t.ticket_id.isin(dup_ids)) & (t.source_system == "legacy_fd")].index
    t = t.drop(index=drop_idx).reset_index(drop=True)

    # Decision 2: normalise CSAT — legacy 0 and helpdesk blank both mean
    # "no response" per policy §8.
    t.loc[(t.source_system == "legacy_fd") & (t.csat_score == 0), "csat_score"] = pd.NA

    # Decision 3: export is UTC (email-thread.txt), shift windows are IST
    # (policy §7). Convert once, up front.
    t["created_ist"] = t["created_at"] + pd.Timedelta(hours=5, minutes=30)
    t["first_response_ist"] = t["first_response_at"] + pd.Timedelta(hours=5, minutes=30)
    t["resolved_ist"] = t["resolved_at"] + pd.Timedelta(hours=5, minutes=30)

    # Decision 4: breach calculation, straight from policy §3.
    t["frt_minutes"] = (t["first_response_at"] - t["created_at"]).dt.total_seconds() / 60
    t["sla_target_min"] = t["channel"].map(SLA_TARGET_MIN)
    t["breached"] = t["frt_minutes"] > t["sla_target_min"]

    # Decision 5: which shift window SHOULD have owned this ticket, by
    # creation time — independent of any agent. This is the structural view.
    t["created_shift"] = t["created_ist"].dt.hour.apply(_shift_for_hour)

    # Decision 6: attribution confidence. tickets.csv only carries the
    # RESOLVING agent, not the first responder. transfers==0 -> resolving
    # agent is very likely also the first responder. transfers>0 ->
    # uncertain; excluded from agent-level blame, still counted structurally.
    t["agent_attribution_reliable"] = t["transfers"] == 0

    return t


def load_agents(data_dir: Path) -> pd.DataFrame:
    a = pd.read_csv(data_dir / "agent.csv")
    a["from_date"] = pd.to_datetime(a["from_date"])
    a["to_date"] = pd.to_datetime(a["to_date"])
    return a


def attach_resolving_agent_shift(t: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    """Point-in-time join: which roster row was active for this agent
    at the ticket's resolution time (falls back to creation time if
    unresolved). Fixed version — computes the anchor and the date
    comparison on the SAME merged frame, not a reindex from the
    pre-merge frame (that reindex silently misaligned duplicate-index
    rows and mis-assigned a handful of tickets to the wrong shift
    across the June 2025 roster change — caught in validation)."""
    t = t.copy()
    t["_anchor"] = t["resolved_ist"].fillna(t["created_ist"])
    merged = t.merge(agents, on="agent_id", how="left", suffixes=("", "_roster"))
    ok = (merged["from_date"] <= merged["_anchor"]) & (
        merged["to_date"].isna() | (merged["to_date"] + pd.Timedelta(days=1) >= merged["_anchor"])
    )
    merged = merged[ok | merged["from_date"].isna()]
    merged = merged.sort_values("from_date").drop_duplicates("ticket_id", keep="last")
    return merged.drop(columns=["_anchor"])


def weekly_report(t: pd.DataFrame, out_dir: Path):
    t = t.copy()
    t["week"] = t["created_ist"].dt.to_period("W-MON").dt.start_time.dt.date

    # View A: structural, by created_shift — no agent identity needed.
    by_shift = (
        t.groupby(["week", "created_shift"])
        .agg(tickets=("ticket_id", "count"), breaches=("breached", "sum"))
        .reset_index()
    )
    by_shift["breach_rate"] = (by_shift["breaches"] / by_shift["tickets"]).round(3)
    by_shift["credit_cost_inr"] = by_shift["breaches"] * BREACH_CREDIT_INR
    by_shift.to_csv(out_dir / "weekly_breach_by_shift.csv", index=False)

    # View B: by resolving agent, reliable-attribution tickets only.
    reliable = t[t.agent_attribution_reliable]
    by_agent = (
        reliable.groupby(["week", "agent_id", "shift", "team"])
        .agg(tickets=("ticket_id", "count"), breaches=("breached", "sum"))
        .reset_index()
    )
    by_agent["breach_rate"] = (by_agent["breaches"] / by_agent["tickets"]).round(3)
    # Decision 7: suppress weeks under 5 tickets — a rate on 2 tickets
    # is noise, not a performance signal.
    by_agent = by_agent[by_agent.tickets >= 5]
    by_agent.to_csv(out_dir / "weekly_breach_by_agent.csv", index=False)

    # Overnight-chat spillover detail — the headline structural issue.
    overnight_chat = t[(t.channel == "chat") & (t.created_shift == "Night")]
    overnight_chat[
        ["ticket_id", "week", "created_ist", "first_response_ist", "frt_minutes", "breached"]
    ].to_csv(out_dir / "overnight_chat_spillover_detail.csv", index=False)

    print(f"Rows: shift report {len(by_shift)}, agent report {len(by_agent)}")
    print(f"Overnight-chat tickets: {len(overnight_chat)}, breached: {overnight_chat.breached.sum()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="./data")
    ap.add_argument("--out", default="./output")
    args = ap.parse_args()

    data_dir = Path(args.data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    t = load_tickets(data_dir)
    agents = load_agents(data_dir)
    t = attach_resolving_agent_shift(t, agents)
    weekly_report(t, out_dir)
    t.to_csv(out_dir / "tickets_enriched.csv", index=False)
    print(f"Done. Output in {out_dir}/")


if __name__ == "__main__":
    main()