import pandas as pd
import matplotlib.pyplot as plt

stats = pd.read_csv("summary_stats.csv")

labels = ["Overall SLA\nBreach Rate", "Emergency SLA\nBreach Rate"]
fifo_vals = [stats.loc[0, "breach_rate"], stats.loc[0, "emergency_breach_rate"]]
prioritized_vals = [stats.loc[1, "breach_rate"], stats.loc[1, "emergency_breach_rate"]]

x = range(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(7, 5))
bars1 = ax.bar([i - width/2 for i in x], fifo_vals, width, label="FIFO (current approach)", color="#c0392b")
bars2 = ax.bar([i + width/2 for i in x], prioritized_vals, width, label="Prioritized (scoring model)", color="#2471a3")

ax.set_ylabel("SLA Breach Rate (%)")
ax.set_title("Dispatch SLA Breach Rate: FIFO vs. Prioritized Scoring")
ax.set_xticks(list(x))
ax.set_xticklabels(labels)
ax.legend()
ax.set_ylim(0, max(fifo_vals + prioritized_vals) * 1.3 + 5)

for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{height:.1f}%", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=10)

plt.tight_layout()
plt.savefig("sla_breach_comparison.png", dpi=150)
print("Saved chart -> sla_breach_comparison.png")
