# DRIFT dataset: live migration across the edge and the vehicle over 5G

Measurements from **DRIFT** (Dynamic Relocation of Intelligent Functions at the extreme Edge), an
enabler that moves running services, with their state and sessions, between edge sites and a
vehicle over a real 5G network. The dataset covers live migration of containers and virtual
machines between edge clusters, live migration of an AI service between a vehicle platform and
the edge, network-driven relocations, and a day of green-energy-aware placement.

Every CSV comes with the script that turns it into the plots and tables in `figures/`.

**Demo video** (click to watch):

[![DRIFT demo: live migration across the edge and the vehicle over 5G](https://img.youtube.com/vi/TtmajA0sB-E/maxresdefault.jpg)](https://youtu.be/TtmajA0sB-E)

**Highlights**

| Result | Value |
|---|---|
| Vehicle <-> edge freeze (median; 9 to the vehicle, 11 to the edge) | 0.89 s to the vehicle, 1.33 s to the edge |
| Data sent over 5G per vehicle migration | 0.4 MiB of a 48 MiB checkpoint |
| Restarting the service instead of migrating it | 3.0 s interruption, state lost |
| VM live migration between edge clusters | at most 109 ms of interruption seen by the user, no session reset |
| Relocations under real 5G uplink congestion | 20 of 20, freeze 1.02 s |
| Green share in the compressed-day replay of 26/10/2026 (DRIFT vs best fixed placement) | 66.3% vs 39.9% |

## Testbed

| Element | Description |
|---|---|
| 5G network | 5G standalone: Amarisoft RAN, Open5GS core, predictive QoS (pQoS) and CAMARA Quality on Demand (QoD) APIs |
| Edge clusters | Two x86 Kubernetes (K3s) clusters joined by an EVPN-stretched Layer 2, so a service keeps its address when it moves |
| Edge site | NVIDIA Jetson AGX Orin (ARM64), partly powered by solar panels |
| Vehicle platform | NVIDIA Jetson Orin Nano (8 GB) with a Quectel RM530N-GL 5G modem, reachable only over 5G |
| Software | K3s, CRI-O, CRIU 4.2 on every site; KubeVirt on the x86 clusters |
| Control | DRIFT controller, migration engine and ETSI MEC 021 interface on a central host |

**Workloads**
- *Between edge clusters:* an Alpine VM streaming a video clip over HTTP, and a YOLOv8n object
  detector in a container serving annotated frames, both to a 5G user.
- *Between the vehicle and the edge:* a recorded dashcam dataset streamed as 720p JPEG frames at
  12 frames per second (FPS) over UDP to a YOLO26n object detector (ONNX Runtime). The Nano
  processes about 6.3 FPS, the AGX Orin the full stream.

All user-facing measurements were taken over 5G.

## Layout

```
data/
  edge-vm-migration/          VM live migration between the edge clusters
  edge-pod-relocation/        container relocation between edge clusters, triggered by pQoS
  edge-decision-timing/       trigger -> migration start (KPI-7) and edge selection time (KPI-5), edge clusters
  vehicle-migration-baseline/ vehicle <-> edge migration sending the full state, no optimization
  vehicle-migration-steps/    the same, adding one technique at a time
  vehicle-migration-campaign/ 20 vehicle <-> edge live migrations with DRIFT
  real-congestion/            relocations under uplink load from other 5G users
  restart-baseline/           restarting the service instead of migrating it
  day-of-placement/           one day of placement under four policies
  energy-inputs/              ECB greenness inputs: the replay's forecast and EV greenness
scripts/                      regenerate every plot and table
figures/                      the plots and table produced by the scripts
```

## Reproduce

Python 3 with `matplotlib` and `numpy`:

```
cd scripts
python3 table_migration_cost.py      # figures/migration_cost.tex
python3 plot_edge_relocation.py      # figures/edge_relocation.pdf
python3 plot_vehicle_freeze.py       # figures/vehicle_freeze.pdf
python3 plot_day_of_placement.py     # figures/day_of_placement.pdf
python3 export_freeze_stages.py      # data/vehicle-migration-campaign/freeze_stages.csv
P_EDGE=8.56 P_VEH=3.57 SUFFIX=_measured python3 analyze_day_of_placement.py ../data/day-of-placement
```

## Conventions

- Times are Unix epoch seconds (UTC) unless a column says otherwise.
- `nano` is the vehicle platform, `orin` the edge site: `nano->orin` = vehicle to edge,
  `orin->nano` = edge to vehicle.
- **Freeze**: the time the service is stopped during a migration. **Gap**: the longest time
  without a processed frame or a served request, as seen by the user.

## Data

### `edge-vm-migration/`
Live migration of a KubeVirt VM between the two edge clusters while it streams video to a user.

`vm_runs.csv`, one row per migration:

| Column | Meaning |
|---|---|
| `run` | Run name |
| `vantage` | Where the stream was measured: the 5G user, or a wired probe |
| `direction` | Source and target cluster |
| `migration_s` | Total migration time (s) |
| `gap_threshold_ms` | Smallest gap the probe records (ms) |
| `max_gap_ms` | Longest gap in the video stream (ms); 0 = none above the threshold |
| `resets` | TCP connections reset |

`gaps_<vantage>_run<N>.csv`: every gap recorded during a run (`utc`, `gap_ms`, `kind`,
`bytes_into_pass`). An empty file means no gap above the threshold.

### `edge-decision-timing/`
Decision timing between the two x86 edge clusters, measured on 16/11/2026 with the video-server pod
(30 MB clip in RAM, floating IP on the stretched Layer 2). Each procedure goes through the ETSI
MEC 021 API with the other cluster as the requested target and moves the pod by CRIU post-copy.
Timestamps come from the container logs: the MEC 021 `POST .../mobility_procedures` (trigger) and
the backend's `POST .../cross-migrate`, which starts the migration (initiation).

| File | Content |
|---|---|
| `kpi7_trigger_to_initiation.csv` | 10 procedures after the controller changes below: trigger and initiation timestamps, `trigger_to_initiated_s` (median 0.58 s, 0.50 to 0.64 s), migration time (median 7.46 s); all 10 completed |
| `kpi7_before_changes.csv` | 2 procedures before the changes (6.98 s and 6.92 s). Both migrations failed because the shared checkpoint store was not mounted on the nodes at the time (fixed before the 10 procedures above) |
| `kpi5_edge_selection.csv` | 10 calls to the controller's edge selection (`GET /candidates`, no target, with a pQoS lookup): median 0.33 s (0.31 to 0.62 s). The pQoS service returned no prediction for the configured UE during these calls (the vehicle was off the 5G network) |
| `kpi7_edge.py` | The script that ran the procedures |

Before the changes, 6.0 s of the 6.9 s went to listing the clusters: the backend probed every
cluster's API live and waited for the timeout of the unreachable vehicle cluster. The changes:
the controller lists clusters without that probe; it keeps the edge nodes' free CPU and memory
refreshed in the background every 10 s instead of reading them during each decision (values up to
10 s old); it passes its chosen node to the backend; and with a requested target it uses the last
known UE context instead of waiting for pQoS (the context does not change such a decision). A
procedure without a target, as started by a pQoS notification, still waits for a fresh context and
was not timed. The vehicle path was not re-measured.

### `edge-pod-relocation/`
Five rounds: the YOLOv8n container serves a 5G user from one edge cluster; at a known time its
path is degraded (egress limited to 1 Mbit/s). A pQoS notification starts an ETSI MEC 021
procedure and DRIFT moves the container to the other cluster, keeping its address.

`rounds.jsonl`, one record per round:

| Field | Meaning |
|---|---|
| `t_limit` | Degradation starts |
| `t_detect` | pQoS notification starts the MEC 021 procedure |
| `t_complete` | Migration complete |
| `detect_s`, `migration_s`, `freeze_s` | Detection delay, migration time, freeze (s) |
| `mig` | Source and target cluster, MiB copied during the freeze |
| `pqos_events` | Times of the pQoS notifications |
| `spurious_before_limit` | Triggers before the degradation (none) |

`requests_round<N>.csv`, every request of the user over 5G:

| Column | Meaning |
|---|---|
| `epoch` | Request time |
| `thread` | Client thread |
| `ttfb_ms` | Time to first byte (ms) |
| `total_ms` | Total request time (ms) |
| `bytes` | Bytes received |
| `status` | `ok` or error |

### `vehicle-migration-baseline/`, `vehicle-migration-steps/`, `vehicle-migration-campaign/`
Live migration of the YOLO26n detector between the vehicle platform and the edge site.

- **baseline**: a plain CRIU migration sending the full state, measured on an earlier build of
  the service (96 to 98 MiB checkpoint), 3 runs per direction.
- **steps**: the same, adding one technique at a time, 2 runs per direction:
  `1-quiesce` (the service drops temporary data before the checkpoint),
  `2-delta-transfer` (only the changes since the previous migration are sent),
  `3-preparation-before-freeze` (all setup done while the service still runs).
- **campaign**: the final DRIFT, 20 migrations (10 round trips, 30 s apart).

`migrations.csv`, one row per migration:

| Column | Meaning |
|---|---|
| `when`, `migration_id`, `status` | Start time, identifier, outcome |
| `direction` | `nano->orin` or `orin->nano` |
| `compute_mode` | Migration mode |
| `freeze_s` | Service frozen (s) |
| `image_mib` | Checkpoint size (MiB) |
| `transfer_s`, `image_mbit_s` | Transfer time (s) and rate (Mbit/s) |
| `wire_mib` | Bytes actually sent over 5G (MiB), campaign only |
| `gap_s` | Longest gap between two processed frames (s) |
| `frames_lost` | Frames of the 12 FPS stream not processed |
| `fps_after` | Processing rate after the migration |
| `freeze_start`, `t_dumped`, `t_sent`, `t_received`, `t_restored` | Timeline of the freeze, campaign only |

`freeze_stages.csv` (campaign), where the freeze time goes:

| Column | Meaning |
|---|---|
| `freeze_s` | Whole freeze (s) |
| `checkpoint_s` | Checkpointing the service |
| `pack_transfer_unpack_s` | Compressing, sending over 5G and unpacking |
| `criu_restore_s` | Restoring the service |
| `control_s` | The rest: coordination before the checkpoint, start of the restore, confirmation |

`logs/<migration_id>.json`: the full log of each migration.

### `real-congestion/`
Two runs of 10 rounds. The service runs at the edge; two other 5G users then load the uplink
with 30 Mbit/s each. DRIFT detects the degradation with its own latency probe and moves the
service to the vehicle. Each run also has 5 healthy control windows.

| File | Content |
|---|---|
| `results.json` | Per round: latency, FPS and unanswered requests with the edge healthy, with the edge congested, and on the vehicle after the move; network round-trip time from the vehicle to the edge with the edge healthy (`A_network_rtt_vehicle_to_edge`) and under load (`B_network_rtt_vehicle_to_edge`); the controls; and a `summary` |
| `network_rtt_samples.csv` | Every sample of DRIFT's latency probe (10 pings from the vehicle to the edge over 5G): `t`, `median_ms`, `p90_ms`, `loss_pct`, `bad` (the sample counts towards a degradation). Both network round-trip fields of `results.json` are medians of these samples over each phase |
| `service_probe.csv` | The vehicle polling the service 5 times per second: `t`, `url` (where it answered), `rtt_ms`, `processed`, `last_processed_at`, `fps`, `packets`, `incomplete` |

### `restart-baseline/`
10 rounds on the vehicle platform: instead of migrating, a fresh copy of the service is
started and the stream is switched to it (what Kubernetes does when it relocates a workload).
`restart_baseline.sh` and `restart_pod.yaml` are the procedure.

`restart_rounds.csv`:

| Column | Meaning |
|---|---|
| `t_pause` | Stream taken away from the running service |
| `t_last_old` | Its last processed frame |
| `t_created`, `t_ip`, `t_health` | New copy created, got its address, answered |
| `t_first` | First frame processed by the new copy |
| `interruption_s` | `t_first - t_last_old` (s) |
| `create_to_first_s` | `t_first - t_created` (s) |

### `day-of-placement/`
A day compressed into 24 slots of 60 s, one per hour, with live migrations over 5G, run once per
policy: `always-vehicle`, `always-edge`, `greedy` (always the greener site, ignoring the
network) and `drift`. Uplink congestion is emulated from 14:00 to 16:00 (camera stream limited
to 2 Mbit/s).

`<policy>.csv`, a sample every ~5 s:

| Column | Meaning |
|---|---|
| `t`, `hour` | Time, hour of the day the slot stands for |
| `edge_green` | Share of renewable energy at the edge site for that hour (PV forecast, 0 to 1) |
| `veh_green` | Renewable share of the vehicle battery's last charge (0 to 1) |
| `congested` | 1 during the emulated congestion |
| `serving` | Where the service runs: `vehicle`, `edge` or `migrating` |
| `processed`, `incomplete` | Frames processed so far, frames lost in transit |
| `fps` | Processing rate |

`summary_measured.csv`, one row per policy: green share (%), total, green and brown energy (Wh),
share of frames processed over the day and in the congested hours, migrations. Energy uses
the measured power the service adds at each site (edge 8.56 W, vehicle 3.57 W net of the 5G
modem), and each slot counts as one hour. `hourly_measured.csv`: the same per hour.

| File | Content |
|---|---|
| `edge_greenness_forecast.json` | The hourly edge greenness used by all policies |
| `<policy>-migrations.json` | The migrations of each policy |
| `drift-engine-log.json` | DRIFT's decisions with their reasons |

## License

[CC BY 4.0](LICENSE). If you use this dataset, please cite it:

> T. Tsourdinis, N. Makris, S. Fdida, T. Korakis. *DRIFT dataset: live migration across the edge
> and the vehicle over 5G*, 2026. https://github.com/teo-tsou/DRIFT-dataset

## Acknowledgment

DRIFT was carried out within the ENVELOPE project, funded by the European Union under the SNS
Joint Undertaking (Horizon Europe, grant agreement No 101139048).

### `energy-inputs/`
Greenness inputs from the ECB energy APIs (GET requests). The supply number of the PV site and the
household production and consumption are removed.

| File | Content |
|---|---|
| `edge_forecast_2026-10-26_used_in_replay.json` | The P50 PV forecast of the edge site for 26/10/2026, fetched on that day and used by every policy of `day-of-placement/`: full responses per hour, with the 15-minute intervals. Requested with a workload energy of 0.0137 kWh per hour (13.7 W, the onboard power profile of 14/10/2026) |
| `ev_greenness.json` | Renewable share of the EV's last charge: 33.76% on 26/10/2026 (the replay day) and 26.76% on 31/10/2026 |
| `edge_forecast_2026-10-31.json` | The same query for 31/10/2026, fetched on 16/11/2026, for reference only (not used by any experiment). The API answers past dates in an `extended_test` mode, and its values for 26/10 differ from the forecast fetched on the day, so only the file fetched on 26/10 reproduces the replay |
