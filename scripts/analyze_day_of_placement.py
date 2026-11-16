#!/usr/bin/env python3
"""analyze_day_of_placement.py DIR: compare the placement policies of a day run.

Reads <policy>.csv (a sample every ~5 s: hour, edge greenness, where the service runs, the
processed-frame counter) and <policy>-migrations.json. Each 60 s slot stands for one hour.
Energy: the power the service adds at its site, P_EDGE and P_VEH in W (env; the dataset uses the
measured 8.56 and 3.57 W with SUFFIX=_measured). Green share: the edge site's PV forecast for
that hour, or the renewable share of the vehicle battery. Writes summary<SUFFIX>.csv and
hourly<SUFFIX>.csv."""
import csv
import json
import os
import sys
from collections import defaultdict

P_EDGE, P_VEH = float(os.environ.get("P_EDGE", 13.7)), float(os.environ.get("P_VEH", 5.0))
VEH_GREEN, SENDER_FPS = 0.75, 12.0
SUFFIX = os.environ.get("SUFFIX", "")
POLICIES = ["always-vehicle", "always-edge", "greedy", "drift"]


def load(out, p):
    rows = list(csv.DictReader(open(f"{out}/{p}.csv")))
    for r in rows:
        r["t"], r["hour"] = float(r["t"]), int(r["hour"])
        r["processed"] = float(r["processed"]) if r["processed"] not in ("", "None") else None
        r["edge_green"] = float(r["edge_green"]) if r["edge_green"] not in ("", "None") else 0.0
        vg = r.get("veh_green")
        r["veh_green"] = float(vg) if vg not in (None, "", "None") else VEH_GREEN
    return rows


def main():
    out = sys.argv[1]
    summary, hourly = [], []
    for p in POLICIES:
        if not os.path.exists(f"{out}/{p}.csv"):
            continue
        rows = load(out, p)
        by_h = defaultdict(list)
        for r in rows:
            by_h[r["hour"]].append(r)
        hours = sorted(by_h)
        tot = green = frames = offered = cong_frames = cong_offered = day_frames = 0.0
        for i, h in enumerate(hours):
            s = by_h[h]
            n = len(s)
            f_edge = sum(r["serving"] == "edge" for r in s) / n
            f_veh = 1 - f_edge
            g = s[0]["edge_green"]
            e = f_edge * P_EDGE + f_veh * P_VEH                      # Wh in this hour
            ge = f_edge * P_EDGE * g + f_veh * P_VEH * s[0]["veh_green"]
            # this hour's own samples only: robust when hours come from different runs
            valid = [r for r in s if r["processed"] is not None]
            p0, p1 = (valid[0]["processed"], valid[-1]["processed"]) if valid else (None, None)
            dt = valid[-1]["t"] - valid[0]["t"] if valid else 0.0
            fr = (p1 - p0) if p0 is not None and p1 >= p0 else 0.0
            fps = fr / dt if dt > 0 else 0.0
            tot, green, frames, offered = tot + e, green + ge, frames + fr, offered + SENDER_FPS * dt
            day_frames += fps * 3600                                 # frames in the hour this slot stands for
            if s[0]["congested"] == "1":
                cong_frames, cong_offered = cong_frames + fr, cong_offered + SENDER_FPS * dt
            hourly.append({"policy": p, "hour": h, "edge_green": g, "edge_frac": round(f_edge, 3),
                           "fps": round(fps, 2), "congested": s[0]["congested"],
                           "energy_wh": round(e, 2), "green_wh": round(ge, 2)})
        try:
            migs = json.load(open(f"{out}/{p}-migrations.json"))
        except FileNotFoundError:
            migs = []
        stalls = [m.get("stall_s") for m in migs if m.get("stall_s")]
        summary.append({
            "policy": p, "green_share_pct": round(100 * green / tot, 1),
            "energy_wh": round(tot, 1), "green_wh": round(green, 1), "brown_wh": round(tot - green, 1),
            "frames_pct": round(100 * frames / offered, 1),
            "frames_congested_pct": round(100 * cong_frames / cong_offered, 1) if cong_offered else "",
            "kframes_day": round(day_frames / 1e3, 1),
            "brown_wh_per_kframe": round((tot - green) / (day_frames / 1e3), 3) if day_frames else "",
            "migrations": len(migs), "mean_stall_s": round(sum(stalls) / len(stalls), 2) if stalls else "",
        })
    for name, data in (("summary", summary), ("hourly", hourly)):
        with open(f"{out}/{name}{SUFFIX}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            w.writeheader(); w.writerows(data)
    keys = list(summary[0].keys())
    print("  ".join(f"{k:>14}" for k in keys))
    for r in summary:
        print("  ".join(f"{str(r[k]):>14}" for k in keys))


if __name__ == "__main__":
    main()
