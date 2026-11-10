"""One day of placement under four policies: (a) green and brown energy with the green
share, (b) share of the 12 FPS stream processed, over the day and in the congested hours.

Data: data/day-of-placement/summary_measured.csv. Output: figures/day_of_placement.pdf"""
import csv
import os

import numpy as np
from plot_style import BLUE, COL_W, DATA, ORANGE, plt, save_fig

POLICIES = [("always-vehicle", "Veh."), ("always-edge", "Edge"), ("greedy", "Greedy"), ("drift", "DRIFT")]
GREEN, BROWN = "#59A14F", "#7F5F3F"   # renewable / grid; also differ in lightness for grayscale

with open(os.path.join(DATA, "day-of-placement", "summary_measured.csv")) as f:
    rows = {r["policy"]: r for r in csv.DictReader(f)}
R = [rows[k] for k, _ in POLICIES]
x = np.arange(len(POLICIES))

fig, (a1, a2) = plt.subplots(1, 2, figsize=(COL_W, 1.15), gridspec_kw=dict(wspace=0.42))

# (a) energy, green + brown
green = [float(r["green_wh"]) for r in R]
brown = [float(r["brown_wh"]) for r in R]
a1.bar(x, green, 0.62, color=GREEN, edgecolor="white", linewidth=0.5, label="green")
a1.bar(x, brown, 0.62, bottom=green, color=BROWN, edgecolor="white", linewidth=0.5, label="brown")
for i, r in enumerate(R):
    a1.text(i, green[i] + brown[i] + 4, f"{float(r['green_share_pct']):.0f}%", ha="center", va="bottom", fontsize=7)
a1.set_ylabel("Energy (Wh)")
a1.set_ylim(0, 270)
a1.legend(loc="upper left", bbox_to_anchor=(0.0, 1.22), ncol=2, handlelength=1, columnspacing=0.8)
a1.set_title("(a)", fontsize=8, y=-0.5)

# (b) frames processed, whole day vs congested hours
w = 0.36
a2.bar(x - w / 2, [float(r["frames_pct"]) for r in R], w, color=BLUE, edgecolor="white", linewidth=0.5, label="day")
a2.bar(x + w / 2, [float(r["frames_congested_pct"]) for r in R], w, color=ORANGE, edgecolor="white", linewidth=0.5,
       label="congested")
a2.set_ylabel("Frames processed (%)", labelpad=1)
a2.set_ylim(0, 100)
a2.legend(loc="upper left", bbox_to_anchor=(0.0, 1.22), ncol=2, handlelength=1, columnspacing=0.8)
a2.set_title("(b)", fontsize=8, y=-0.5)

for a in (a1, a2):
    a.set_xticks(x)
    a.set_xticklabels([n for _, n in POLICIES], fontsize=6.5)
    a.tick_params(axis="x", length=0, pad=2)
    a.set_xlim(-0.6, 3.6)
    a.get_xticklabels()[-1].set_fontweight("bold")
    for i, t in enumerate(a.get_xticklabels()):
        t.set_y(-0.08 if i % 2 else 0)   # stagger, so the labels never touch

save_fig(fig, "day_of_placement")
