"""Relocation between edge clusters triggered by a pQoS prediction, seen by the 5G user.

Data: data/edge-pod-relocation (rounds.jsonl, requests_round<N>.csv). Per 1 s bin and round:
throughput = bytes received, response time = median time to first byte. Plotted: median over
the 5 rounds, band = min..max. Output: figures/edge_relocation.pdf"""
import csv
import json
import math
import os

import numpy as np

from plot_style import BLUE, COL_W, DATA, ORANGE, SHADE, plt, save_fig

D = os.path.join(DATA, "edge-pod-relocation")
W0, W1 = -20, 75                      # seconds around the start of the degradation
T_DEG = -W0                           # plotted time axis starts at 0; the degradation starts at T_DEG

with open(os.path.join(D, "rounds.jsonl")) as f:
    rounds = [json.loads(line) for line in f]
nb = W1 - W0
mbps = np.zeros((len(rounds), nb))
resp = np.full((len(rounds), nb), np.nan)
detect, complete = [], []
for i, r in enumerate(rounds):
    t_lim = r["t_limit"]
    detect.append(r["t_detect"] - t_lim)
    complete.append(r["t_complete"] - t_lim)
    per_bin = {}
    with open(os.path.join(D, f"requests_round{r['round']}.csv")) as f:
        for req in csv.DictReader(f):
            if req.get("status") != "ok":
                continue
            b = math.floor(float(req["epoch"]) - t_lim - W0)   # floor: int() would fold -1..0 into bin 0
            if 0 <= b < nb:
                per_bin.setdefault(b, []).append((float(req["bytes"]), float(req["ttfb_ms"])))
    for b, reqs in per_bin.items():
        mbps[i, b] = sum(n for n, _ in reqs) * 8 / 1e6
        resp[i, b] = np.median([t for _, t in reqs])
t = np.arange(nb) + 0.5
t_det, t_mig = float(np.median(detect)) + T_DEG, float(np.median(complete)) + T_DEG
print(f"rounds {len(rounds)}, detect {np.round(detect, 1)}, complete {np.round(complete, 1)}")

fig, (a1, a2) = plt.subplots(2, 1, figsize=(COL_W, 1.85), sharex=True,
                             gridspec_kw=dict(hspace=0.12))
for ax in (a1, a2):
    ax.axvspan(t_det, t_mig, color=SHADE, linewidth=0, zorder=0)
    ax.axvline(T_DEG, color="0.45", linewidth=0.7, linestyle=":", zorder=1)
a1.fill_between(t, mbps.min(0), mbps.max(0), step="mid", color=BLUE, alpha=0.25, linewidth=0)
a1.step(t, np.median(mbps, 0), where="mid", color=BLUE)
a1.set_ylim(0, 12)
a1.set_yticks([0, 4, 8, 12])
a1.set_ylabel("Throughput\n(Mbit/s)")
a1.text(T_DEG + 1, 11.3, "degradation", fontsize=8, va="top")
with np.errstate(all="ignore"):
    lo, hi, med = np.nanmin(resp, 0), np.nanmax(resp, 0), np.nanmedian(resp, 0)
a2.fill_between(t, lo, hi, step="mid", color=ORANGE, alpha=0.25, linewidth=0)
a2.step(t, med, where="mid", color=ORANGE)
a2.set_yscale("log")
a2.set_ylim(40, 5000)
a2.set_yticks([100, 1000], ["100", "1000"])
a2.minorticks_off()
a2.set_ylabel("Response\ntime (ms)")
a2.set_xlabel("Time (s)")
a2.set_xlim(0, W1 - W0)
# legend keys show both panels' colours: blue = throughput, orange = response time
Patch = plt.matplotlib.patches.Patch
HandlerTuple = plt.matplotlib.legend_handler.HandlerTuple
h = [(plt.Line2D([], [], color=BLUE), plt.Line2D([], [], color=ORANGE)),
     (Patch(facecolor=BLUE, alpha=0.25), Patch(facecolor=ORANGE, alpha=0.25)),
     Patch(facecolor=SHADE)]
a1.legend(h, ["median (5 rounds)", "min–max", "detected → migrated"],
          handler_map={tuple: HandlerTuple(ndivide=None, pad=0.2)},
          loc="lower left", ncols=2, mode="expand", bbox_to_anchor=(0, 1.02, 1, 0.2),
          handlelength=2.2, borderaxespad=0)
save_fig(fig, "edge_relocation")
