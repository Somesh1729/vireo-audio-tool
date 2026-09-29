import argparse
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESHUFFLE_DATE = "2025-07"  # first full month after the 30 Jun 2025 roster change


def chart_monthly_breach_rate(t: pd.DataFrame, out_dir: Path):
    t = t.copy()
    t["month"] = t["created_ist"].dt.to_period("M").astype(str)
    m = t.groupby("month").agg(tickets=("ticket_id", "count"), breaches=("breached", "sum"))
    m["breach_rate"] = m["breaches"] / m["tickets"]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(m.index, m["breach_rate"] * 100, marker="o", color="#c0392b")
    ax.axvline(x=RESHUFFLE_DATE, color="gray", linestyle="--", alpha=0.6)
    ax.text(RESHUFFLE_DATE, ax.get_ylim()[1]*0.92, " Indore Night shift\n eliminated (30 Jun 2025)",
            fontsize=8, color="gray")
    ax.set_ylabel("Breach rate (%)")
    ax.set_title("Monthly first-response SLA breach rate — company-wide")
    plt.xticks(rotation=60, fontsize=8)
    plt.tight_layout()
    fig.savefig(out_dir / "chart_monthly_breach_rate.png", dpi=140)
    plt.close(fig)


def chart_overnight_vs_daytime_chat(t: pd.DataFrame, out_dir: Path):
    chat = t[t.channel == "chat"].copy()
    chat["month"] = chat["created_ist"].dt.to_period("M").astype(str)
    chat["window"] = chat["created_shift"].apply(lambda s: "Overnight (Night window)" if s == "Night" else "Daytime")
    m = chat.groupby(["month", "window"]).agg(
        tickets=("ticket_id", "count"), breaches=("breached", "sum")
    ).reset_index()
    m["breach_rate"] = m["breaches"] / m["tickets"]
    pivot = m.pivot(index="month", columns="window", values="breach_rate") * 100

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for col, color in zip(pivot.columns, ["#c0392b", "#2980b9"]):
        ax.plot(pivot.index, pivot[col], marker="o", label=col, color=color)
    ax.axvline(x=RESHUFFLE_DATE, color="gray", linestyle="--", alpha=0.6)
    ax.set_ylabel("Chat breach rate (%)")
    ax.set_title("Chat SLA breach rate: overnight vs. daytime tickets")
    ax.legend()
    plt.xticks(rotation=60, fontsize=8)
    plt.tight_layout()
    fig.savefig(out_dir / "chart_overnight_vs_daytime_chat.png", dpi=140)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./output")
    args = ap.parse_args()
    out_dir = Path(args.out)

    t = pd.read_csv(out_dir / "tickets_enriched.csv")
    t["created_ist"] = pd.to_datetime(t["created_ist"])

    chart_monthly_breach_rate(t, out_dir)
    chart_overnight_vs_daytime_chat(t, out_dir)
    print(f"Charts saved to {out_dir}/")


if __name__ == "__main__":
    main()