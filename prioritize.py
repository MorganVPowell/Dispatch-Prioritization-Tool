"""
Dispatch Prioritization Tool
-----------------------------
Problem: When requests are dispatched strictly first-come-first-served (FIFO),
urgent/emergency requests can get stuck behind low-priority ones simply
because they were submitted later, causing SLA breaches on the requests
that matter most.

This tool scores each request on three factors and re-orders the queue
so urgent, time-sensitive, and nearby requests get handled first,
then simulates dispatch under both approaches to measure the impact.

Scoring formula (weights are a product decision, explained in README):
    score = 0.5 * urgency_score + 0.3 * sla_risk_score + 0.2 * proximity_score

- urgency_score: emergency=1.0, standard=0.5, low=0.0
- sla_risk_score: how close the request is to breaching its SLA window
  (higher = more time pressure)
- proximity_score: closer requests score higher (faster to serve, keeps
  the queue moving)
"""

import pandas as pd

URGENCY_SCORE_MAP = {"emergency": 1.0, "standard": 0.5, "low": 0.0}

# Weights: urgency matters most (matches real-world triage), SLA risk next,
# distance is a minor tiebreaker. These are tunable — see README for rationale.
WEIGHT_URGENCY = 0.5
WEIGHT_SLA_RISK = 0.3
WEIGHT_PROXIMITY = 0.2

# Assume a small team of technicians working in parallel (realistic for a
# regional dispatch operation), each processing one request at a time.
# Average handling time per request, in minutes.
AVG_HANDLING_MINUTES = 25
NUM_TECHNICIANS = 6


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["urgency_score"] = df["urgency"].map(URGENCY_SCORE_MAP)

    # SLA risk: shorter SLA windows carry more inherent time pressure.
    # Normalize so tightest window (60 min) = highest risk.
    max_sla = df["sla_minutes"].max()
    df["sla_risk_score"] = 1 - (df["sla_minutes"] / max_sla)

    # Proximity: closer requests score higher.
    max_distance = df["distance_miles"].max()
    df["proximity_score"] = 1 - (df["distance_miles"] / max_distance)

    df["priority_score"] = (
        WEIGHT_URGENCY * df["urgency_score"]
        + WEIGHT_SLA_RISK * df["sla_risk_score"]
        + WEIGHT_PROXIMITY * df["proximity_score"]
    )

    return df


def simulate_dispatch(df: pd.DataFrame, policy: str) -> pd.DataFrame:
    """
    Event-driven simulation: requests arrive over time (per their real
    submitted_time), and get pulled from a *live* waiting queue whenever a
    technician becomes free. This mirrors how a real dispatch queue works
    (you can't reorder jobs that haven't been requested yet).

    policy: "fifo" picks the earliest-arrived waiting request.
            "prioritized" picks the highest priority_score among waiting
            requests currently in the queue.
    """
    records = df.to_dict("records")
    records.sort(key=lambda r: r["submitted_time"])  # true arrival order

    shift_start = records[0]["submitted_time"]
    tech_free_at = [shift_start] * NUM_TECHNICIANS

    pending = list(records)   # not yet arrived (by submitted_time)
    waiting = []               # arrived, waiting to be assigned
    results = []

    while pending or waiting:
        next_tech_idx = tech_free_at.index(min(tech_free_at))
        tech_time = tech_free_at[next_tech_idx]

        # Move any requests that have arrived by tech_time into the waiting queue.
        pending.sort(key=lambda r: r["submitted_time"])
        while pending and pending[0]["submitted_time"] <= tech_time:
            waiting.append(pending.pop(0))

        # If nobody is waiting yet, jump forward to the next arrival.
        if not waiting:
            tech_time = pending[0]["submitted_time"]
            waiting.append(pending.pop(0))

        # Pick the next job per policy.
        if policy == "fifo":
            waiting.sort(key=lambda r: r["submitted_time"])
        else:  # prioritized
            waiting.sort(key=lambda r: r["priority_score"], reverse=True)

        job = waiting.pop(0)
        start_time = max(tech_time, job["submitted_time"])
        finish_time = start_time + pd.Timedelta(minutes=AVG_HANDLING_MINUTES)
        tech_free_at[next_tech_idx] = finish_time

        job["completion_time"] = finish_time
        results.append(job)

    ordered = pd.DataFrame(results)
    ordered["sla_deadline"] = ordered["submitted_time"] + pd.to_timedelta(ordered["sla_minutes"], unit="m")
    ordered["breached_sla"] = ordered["completion_time"] > ordered["sla_deadline"]

    return ordered


def summarize(label: str, ordered: pd.DataFrame):
    total = len(ordered)
    breached = ordered["breached_sla"].sum()
    breach_rate = breached / total * 100

    emergency = ordered[ordered["urgency"] == "emergency"]
    emergency_breached = emergency["breached_sla"].sum()
    emergency_rate = (emergency_breached / len(emergency) * 100) if len(emergency) else 0

    print(f"\n--- {label} ---")
    print(f"Total requests: {total}")
    print(f"Overall SLA breach rate: {breach_rate:.1f}% ({breached}/{total})")
    print(f"Emergency SLA breach rate: {emergency_rate:.1f}% ({emergency_breached}/{len(emergency)})")

    return {
        "label": label,
        "total": total,
        "breach_rate": breach_rate,
        "emergency_breach_rate": emergency_rate,
    }


if __name__ == "__main__":
    df = pd.read_csv("sample_requests.csv", parse_dates=["submitted_time"])
    df = compute_scores(df)

    # FIFO: dispatch strictly in the order requests came in.
    fifo_result = simulate_dispatch(df, policy="fifo")
    fifo_stats = summarize("FIFO (first-come, first-served)", fifo_result)

    # Prioritized: whenever a tech frees up, serve the highest-scoring
    # request currently waiting in the queue.
    prioritized_result = simulate_dispatch(df, policy="prioritized")
    prioritized_stats = summarize("Prioritized (score-based)", prioritized_result)

    improvement = fifo_stats["emergency_breach_rate"] - prioritized_stats["emergency_breach_rate"]
    print(f"\n>>> Emergency SLA breach rate improved by {improvement:.1f} percentage points "
          f"under prioritized dispatch.")

    fifo_result.to_csv("fifo_results.csv", index=False)
    prioritized_result.to_csv("prioritized_results.csv", index=False)

    # Save summary stats for the chart/report step.
    pd.DataFrame([fifo_stats, prioritized_stats]).to_csv("summary_stats.csv", index=False)
