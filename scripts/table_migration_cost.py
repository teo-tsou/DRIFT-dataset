"""Migration cost per class (medians), written as a LaTeX table.

Data: data/edge-vm-migration, data/edge-pod-relocation, data/vehicle-migration-campaign.
Output: figures/migration_cost.tex"""
import csv
import glob
import json
import os
import statistics as st

from plot_style import FIG_DIR, DATA


def mm(v, fmt="{:.2f}"):
    v = [x for x in v if x is not None]
    return fmt.format(st.median(v))


rows = []
# edge<->edge VM: the UE-over-5G runs (the wired runs only add migration time)
with open(os.path.join(DATA, "edge-vm-migration", "vm_runs.csv")) as f:
    vm = [r for r in csv.DictReader(f) if r["vantage"] == "UE over 5G"]
rows.append(("Edge$\\leftrightarrow$edge, VM", "KubeVirt pre-copy", len(vm),
             mm([float(r["migration_s"]) for r in vm], "{:.1f}"), "--",
             f"$\\le${max(int(r['max_gap_ms']) for r in vm)}\\,ms", "--",
             f"{sum(int(r['resets']) for r in vm)} resets"))

# edge<->edge pod: the YOLOv8n object-detection pod under cross-cluster CRIU post-copy.
# UE-side stall = longest time with no completed request between the detection and
# 15 s after the migration completed
D = os.path.join(DATA, "edge-pod-relocation")
with open(os.path.join(D, "rounds.jsonl")) as f:
    kr = [json.loads(line) for line in f]
stalls = []
for r in kr:
    with open(os.path.join(D, f"requests_round{r['round']}.csv")) as f:
        done = sorted(float(q["epoch"]) + float(q["total_ms"]) / 1000 for q in csv.DictReader(f)
                      if q.get("status") == "ok")
    win = [t for t in done if r["t_detect"] <= t <= r["t_complete"] + 15]
    stalls.append(max(b - a for a, b in zip(win, win[1:])))
rows.append(("Edge$\\leftrightarrow$edge, pod", "CRIU post-copy", len(kr),
             mm([r["migration_s"] for r in kr], "{:.1f}"), mm([r["freeze_s"] for r in kr]),
             mm(stalls) + "\\,s", mm([r["mig"]["net_freeze_mib"] for r in kr], "{:.1f}") + " MiB",
             "0 resets"))

# vehicle<->edge pod (campaign of 10 round trips). Stall seen by the user = the
# longest gap between two frames processed by the service (gap_s, recorded by the receiver).
C = os.path.join(DATA, "vehicle-migration-campaign")
with open(os.path.join(C, "migrations.csv")) as f:
    camp = list(csv.DictReader(f))
total = {}
for p in glob.glob(os.path.join(C, "logs", "*.json")):
    with open(p) as f:
        j = json.load(f)
    if j.get("started_at") and j.get("finished_at"):
        total[j["id"]] = j["finished_at"] - j["started_at"]
num = lambda rs, k: [float(r[k]) for r in rs if r[k]]
for key, label in (("orin->nano", "Edge$\\rightarrow$vehicle"), ("nano->orin", "Vehicle$\\rightarrow$edge")):
    rs = [r for r in camp if r["direction"] == key and r["status"] == "completed"]
    rows.append((label + ", pod", "CRIU + delta", len(rs),
                 mm([total.get(r["migration_id"]) for r in rs], "{:.1f}"),
                 mm(num(rs, "freeze_s")), mm(num(rs, "gap_s")) + "\\,s",
                 mm(num(rs, "wire_mib")) + " MiB", mm(num(rs, "frames_lost"), "{:.0f}") + " frames"))

tex = [r"\begin{table*}[t]",
       r"\centering",
       r"\caption{Migration cost per class}",
       r"\label{tab:migration_cost}",
       r"\footnotesize",
       r"\setlength{\tabcolsep}{4pt}",
       r"\begin{tabular}{llrllllr}",
       r"\toprule",
       r"Class & Mechanism & $n$ & Migration (s) & Freeze (s) & Stall seen by user & Data moved & Loss \\",
       r"\midrule"]
tex += [" & ".join(str(c) for c in r) + r" \\" for r in rows]
tex += [r"\bottomrule", r"\end{tabular}",
        r"\\[3pt]\parbox{\textwidth}{\footnotesize Median over $n$ migrations, client over 5G. Stall: longest gap seen by the user. Data moved: copied in the freeze (edge pod) or sent over 5G (vehicle).}",
        r"\end{table*}"]
out = os.path.join(FIG_DIR, "migration_cost.tex")
with open(out, "w") as f:
    f.write("\n".join(tex) + "\n")
print("\n".join(" | ".join(map(str, r)) for r in rows))
print("Saved:", out)
