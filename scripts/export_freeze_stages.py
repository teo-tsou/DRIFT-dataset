"""Export the stages of every vehicle <-> edge migration of the campaign to
data/vehicle-migration-campaign/freeze_stages.csv (one row per migration): the freeze and its
checkpoint, transfer, restore and control parts, parsed from the migration logs (logs/*.json)."""
import csv, glob, json, os, re
DATA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"))

C = os.path.join(DATA, "vehicle-migration-campaign")
rows = []
for p in sorted(glob.glob(os.path.join(C, "logs", "*.json"))):
    j = json.load(open(p)); o = j.get("output", "")
    m = re.search(r"timeline from freeze start: (.*)", o); fr = re.search(r"freeze window ~([\d.]+)s", o)
    if not (m and fr and j.get("completed")):
        continue
    t = {k: float(v) for k, v in re.findall(r"(\S+) \+([\d.]+)s", m.group(1))}
    if not all(k in t for k in ("ckpt-start", "ckpt-done", "received", "criu-start", "criu-end")):
        continue
    f = float(fr.group(1))
    ck, tx, rs = t["ckpt-done"] - t["ckpt-start"], t["received"] - t["ckpt-done"], t["criu-end"] - t["criu-start"]
    rows.append({"migration_id": j["id"], "started_at": j["started_at"],
                 "direction": "vehicle->edge" if j["src_cluster"] == "drift-vehicle" else "edge->vehicle",
                 "freeze_s": f, "checkpoint_s": round(ck, 3), "pack_transfer_unpack_s": round(tx, 3),
                 "criu_restore_s": round(rs, 3), "control_s": round(f - ck - tx - rs, 3)})
rows.sort(key=lambda r: r["started_at"])
out = os.path.join(C, "freeze_stages.csv")
with open(out, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"{len(rows)} migrations -> {out}")
