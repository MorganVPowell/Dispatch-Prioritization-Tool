"""
Generates a sample dataset of service dispatch requests.
Simulates the kind of data you'd see in a real dispatch queue:
urgency level, distance from nearest available driver/tech,
SLA window, and submission time.
"""

import random
import pandas as pd
from datetime import datetime, timedelta

random.seed(42)  # reproducible results

NUM_REQUESTS = 120

URGENCY_LEVELS = {
    "emergency": {"weight": 3, "sla_minutes": 60},
    "standard":  {"weight": 2, "sla_minutes": 180},
    "low":       {"weight": 1, "sla_minutes": 480},
}

URGENCY_DISTRIBUTION = ["emergency"] * 15 + ["standard"] * 55 + ["low"] * 30  # roughly realistic mix

def generate_requests(n=NUM_REQUESTS):
    start_time = datetime(2026, 9, 7, 8, 0)  # 8:00 AM shift start
    rows = []

    for i in range(n):
        urgency = random.choice(URGENCY_DISTRIBUTION)
        sla_minutes = URGENCY_LEVELS[urgency]["sla_minutes"]

        # requests trickle in across an 8-hour shift
        submitted_offset = random.randint(0, 8 * 60)
        submitted_time = start_time + timedelta(minutes=submitted_offset)

        distance_miles = round(random.uniform(0.5, 25.0), 1)

        rows.append({
            "request_id": f"REQ-{i+1:04d}",
            "urgency": urgency,
            "sla_minutes": sla_minutes,
            "distance_miles": distance_miles,
            "submitted_time": submitted_time,
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("submitted_time").reset_index(drop=True)
    return df

if __name__ == "__main__":
    df = generate_requests()
    df.to_csv("sample_requests.csv", index=False)
    print(f"Generated {len(df)} sample requests -> sample_requests.csv")
    print(df["urgency"].value_counts())
