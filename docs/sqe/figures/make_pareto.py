"""Draw the defect Pareto chart from the counts in CONSOLIDATED_DEFECT_LOG.md section 3.

Run: uv run --with matplotlib python docs/sqe/figures/make_pareto.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CATEGORIES = [  # (category, defect ids) - must match the defect log table
    ("Input validation", ["W-01", "W-02", "W-04", "W-05", "A3-D01"]),
    ("Rule not enforced /\nAPI contract", ["W-03", "W-06", "W-07", "W-08"]),
    ("Security config /\ndependencies", ["A3-D02", "A3-D04", "A3-D05"]),
    ("Logic error", ["A3-D06", "D-Z01"]),
    ("Accessibility", ["A3-D03"]),
]

names = [c for c, _ in CATEGORIES]
counts = [len(ids) for _, ids in CATEGORIES]
total = sum(counts)
cum, s = [], 0
for c in counts:
    s += c
    cum.append(100 * s / total)

fig, ax = plt.subplots(figsize=(8, 4.5))
bars = ax.bar(names, counts, color="#4C6A92")
ax.set_ylabel("Defects")
ax.set_ylim(0, max(counts) + 1)
for b, c in zip(bars, counts):
    ax.text(b.get_x() + b.get_width() / 2, c + 0.1, str(c), ha="center", va="bottom")
ax2 = ax.twinx()
ax2.plot(names, cum, color="#C0504D", marker="o")
ax2.axhline(80, color="#888888", linestyle="--", linewidth=1)
ax2.set_ylim(0, 105)
ax2.set_ylabel("Cumulative %")
for x, y in zip(names, cum):
    ax2.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=8)
ax.set_title(f"Defects by category (n = {total})")
plt.xticks(fontsize=8)
ax.tick_params(axis="x", labelsize=8)
fig.tight_layout()
out = Path(__file__).with_name("pareto_defects.png")
fig.savefig(out, dpi=150)
print("written", out)
