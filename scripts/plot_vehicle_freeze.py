"""Vehicle <-> edge live migration: (a) freeze of a full-image baseline and of DRIFT,
(b) stages of the median DRIFT freeze.

Data: data/vehicle-migration-baseline, data/vehicle-migration-campaign (logs/*.json).
Output: figures/vehicle_freeze.pdf"""
import csv, glob, json, os, re, statistics as st
import numpy as np
from plot_style import BLUE, COL_W, COLORS, GRAY, DATA, ORANGE, plt, save_fig

DIRS = [("nano->orin", "Vehicle→edge"), ("orin->nano", "Edge→vehicle")]
with open(os.path.join(DATA, "vehicle-migration-baseline", "migrations.csv")) as f:
    base = [r for r in csv.DictReader(f) if r["status"] == "completed"]
C = os.path.join(DATA, "vehicle-migration-campaign")
hops = {k: [] for k, _ in DIRS}
for p in glob.glob(os.path.join(C, "logs", "*.json")):
    j = json.load(open(p)); o = j.get("output", "")
    m = re.search(r"timeline from freeze start: (.*)", o); fr = re.search(r"freeze window ~([\d.]+)s", o)
    if not (m and fr and j.get("completed")): continue
    t = {k: float(v) for k, v in re.findall(r"(\S+) \+([\d.]+)s", m.group(1))}
    if not all(k in t for k in ("ckpt-start", "ckpt-done", "received", "criu-start", "criu-end")): continue
    d = "nano->orin" if j["src_cluster"] == "drift-vehicle" else "orin->nano"
    hops[d].append((j["started_at"], float(fr.group(1)), t))

fig, (a1, a2) = plt.subplots(2, 1, figsize=(COL_W, 2.15), gridspec_kw=dict(height_ratios=[1, 1.15], hspace=1.05))
# (a) baseline vs DRIFT, log axis
y = np.arange(len(DIRS))
for i, (k, lab) in enumerate(DIRS):
    b = st.median(float(r["freeze_s"]) for r in base if r["direction"] == k)
    dfz = st.median(f for _, f, _ in hops[k])
    a1.barh(i + 0.18, b, 0.34, color=COLORS[3], label="baseline CRIU" if i == 0 else None)
    a1.barh(i - 0.18, dfz, 0.34, color=BLUE, label="DRIFT" if i == 0 else None)
    a1.text(b * 1.12, i + 0.18, f"{b:.0f} s", va="center", fontsize=7.5)
    a1.text(dfz * 1.12, i - 0.18, f"{dfz:.2f} s  ({b / dfz:.0f}× shorter)", va="center", fontsize=7.5)
    print(k, "baseline median", b, "DRIFT median", dfz, "n", len(hops[k]))
a1.set_xscale("log"); a1.set_xlim(0.5, 400)
a1.set_xticks([1, 10, 100], ["1", "10", "100"]); a1.minorticks_off()
a1.set_yticks(y, [l for _, l in DIRS]); a1.invert_yaxis()
a1.set_xlabel("Freeze (s), median")
a1.legend(loc="lower left", ncols=2, bbox_to_anchor=(0, 1.02, 1, 0.2), mode="expand", borderaxespad=0, fontsize=7.5)
# (b) anatomy of the median DRIFT hop
STAGES = [("checkpoint", COLORS[4]), ("pack + 5G transfer + unpack", COLORS[1]), ("CRIU restore", COLORS[7]), ("control", COLORS[9])]
for i, (k, lab) in enumerate(DIRS):
    lst = sorted(hops[k], key=lambda h: h[1]); _, f, t = lst[len(lst) // 2]
    seg = {"checkpoint": t["ckpt-done"] - t["ckpt-start"], "pack + 5G transfer + unpack": t["received"] - t["ckpt-done"],
           "CRIU restore": t["criu-end"] - t["criu-start"]}
    seg["control"] = f - sum(seg.values())          # orchestration before the dump, restore start, confirmation
    left = 0
    for name, col in STAGES:
        a2.barh(i, seg[name], 0.55, left=left, color=col, label=name if i == 0 else None)
        if seg[name] > 0.12: a2.text(left + seg[name] / 2, i, f"{seg[name]:.2f}", ha="center", va="center", fontsize=7, color="black")
        left += seg[name]
    a2.text(left + 0.02, i, f"{f:.2f} s", va="center", fontsize=7.5)
    print(k, "median hop", f, {n: round(v, 2) for n, v in seg.items()})
a2.set_yticks(y, [l for _, l in DIRS]); a2.invert_yaxis(); a2.set_xlim(0, 1.6)
a2.set_xlabel("DRIFT freeze, median hop (s)")
a2.legend(loc="lower left", ncols=2, bbox_to_anchor=(0, 1.02, 1, 0.2), mode="expand", borderaxespad=0, fontsize=7, handlelength=1)
for ax, lbl in ((a1, "(a)"), (a2, "(b)")):
    ax.text(-0.27, 1.0, lbl, transform=ax.transAxes, fontsize=8, va="bottom")
save_fig(fig, "vehicle_freeze")
