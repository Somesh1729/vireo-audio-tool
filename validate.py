import argparse
from pathlib import Path
import pandas as pd


def independent_breach_calc(row):
    """Deliberately separate re-implementation — no shared code with
    run_report.py — used only to cross-check its output."""
    targets = {"chat": 15, "voice": 120, "social": 240, "email": 480}
    delta_min = (row["first_response_at"] - row["created_at"]).total_seconds() / 60
    return delta_min > targets[row["channel"]]


def run_sample_check(data_dir: Path, out_dir: Path, n=50, seed=42):
    t = pd.read_csv(data_dir / "tickets.csv")
    for c in ["created_at", "first_response_at"]:
        t[c] = pd.to_datetime(t[c])
    dup_ids = t.ticket_id[t.ticket_id.duplicated(keep=False)]
    t = t.drop(index=t[(t.ticket_id.isin(dup_ids)) & (t.source_system == "legacy_fd")].index)

    sample = t.sample(n=n, random_state=seed)
    sample["recomputed_breach"] = sample.apply(independent_breach_calc, axis=1)

    enriched = pd.read_csv(out_dir / "tickets_enriched.csv")
    check = sample.merge(enriched[["ticket_id", "breached"]], on="ticket_id")
    mismatches = check[check["recomputed_breach"] != check["breached"]]

    print(f"[Sample check] n={len(check)}  mismatches={len(mismatches)}  "
          f"agreement={1 - len(mismatches)/len(check):.1%}")
    if len(mismatches):
        print(mismatches[["ticket_id", "channel", "created_at",
                           "first_response_at", "breached", "recomputed_breach"]])
    return len(mismatches) == 0


def run_edge_cases(out_dir: Path):
    enriched = pd.read_csv(out_dir / "tickets_enriched.csv")
    enriched["resolved_ist"] = pd.to_datetime(enriched["resolved_ist"])
    ok = True

    # Edge case: agent who moved shift on 2025-06-30 (A3002, Night -> Day)
    a = enriched[enriched.agent_id == "A3002"].dropna(subset=["resolved_ist"])
    before = a[a.resolved_ist < "2025-06-30"]["shift"].unique().tolist()
    after = a[a.resolved_ist >= "2025-06-30"]["shift"].unique().tolist()
    passed = before == ["Night"] and after == ["Day"]
    ok &= passed
    print(f"[Edge: moved-agent roster join] before={before} after={after} "
          f"{'PASS' if passed else 'FAIL'}")

    # Edge case: midnight-crossing shift boundary classification
    tests = {0: "Night", 5: "Night", 6: "Morning", 13: "Morning",
             14: "Day", 21: "Day", 22: "Night", 23: "Night"}
    def shift_for_hour(h):
        if 6 <= h < 14: return "Morning"
        if 14 <= h < 22: return "Day"
        return "Night"
    passed = all(shift_for_hour(h) == v for h, v in tests.items())
    ok &= passed
    print(f"[Edge: midnight-crossing shift boundaries] {'PASS' if passed else 'FAIL'}")

    # Edge case: dedup didn't drop or duplicate any real ticket
    raw = pd.read_csv("data/tickets.csv")
    expected_after_dedup = len(raw) - raw.ticket_id.duplicated(keep=False).sum() // 2
    passed = len(enriched) == expected_after_dedup
    ok &= passed
    print(f"[Edge: dedup row count] raw={len(raw)} enriched={len(enriched)} "
          f"expected={expected_after_dedup} {'PASS' if passed else 'FAIL'}")

    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="./data")
    ap.add_argument("--out", default="./output")
    args = ap.parse_args()
    data_dir, out_dir = Path(args.data), Path(args.out)

    r1 = run_sample_check(data_dir, out_dir)
    r2 = run_edge_cases(out_dir)
    print("\nALL CHECKS PASSED" if (r1 and r2) else "\nSOME CHECKS FAILED — see above")


if __name__ == "__main__":
    main()