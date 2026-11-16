#!/bin/bash
# Restart baseline on the vehicle Jetson (run there): N rounds of
#   pause the stream to the running YOLO (t_last = its last processed frame),
#   create a fresh pod, aim the stream at it, wait for its first processed frame,
#   then resume the original and delete the fresh pod.
# Interruption = first frame of the fresh instance - last frame of the old one.
set -u
N=${1:-10}; OLD=${OLD:-10.48.0.24}; K="sudo -n k3s kubectl"; T="sudo -n /usr/local/sbin/drift-yolo-target"
now() { date +%s.%N; }
h() { curl -s -m 1 "http://$1:9000/health"; }
jget() { python3 -c "import sys,json; d=json.loads(sys.stdin.read() or '{}'); print(d.get('$1',''))"; }
echo "round,t_pause,t_last_old,t_created,t_ip,t_health,t_first,interruption_s,create_to_first_s"
for i in $(seq 1 $N); do
  $K delete pod emt-yolo-restart --ignore-not-found --wait=true >/dev/null 2>&1
  sleep 5
  tp=$(now); $T pause >/dev/null
  tl=$(h $OLD | jget last_processed_at)
  tc=$(now); $K apply -f /tmp/restart_pod.yaml >/dev/null
  ip=""; while [ -z "$ip" ]; do ip=$($K get pod emt-yolo-restart -o jsonpath='{.status.podIP}' 2>/dev/null); [ -z "$ip" ] && sleep 0.05; done
  ti=$(now); $T aim local $ip >/dev/null
  th=""; tf=""
  for _ in $(seq 1 1200); do
    r=$(h $ip)
    if [ -n "$r" ]; then
      [ -z "$th" ] && th=$(now)
      p=$(echo "$r" | jget processed)
      if [ -n "$p" ] && [ "$p" != "0" ]; then tf=$(echo "$r" | jget last_processed_at); break; fi
    fi
    sleep 0.05
  done
  $T resume >/dev/null
  python3 -c "
tp,tl,tc,ti,th,tf=[float(x) if x else float('nan') for x in '$tp $tl $tc $ti ${th:-} ${tf:-}'.split()+['','']][:6]
print(f'$i,{tp:.3f},{tl:.3f},{tc:.3f},{ti:.3f},{th:.3f},{tf:.3f},{tf-tl:.3f},{tf-tc:.3f}')"
  $K delete pod emt-yolo-restart --wait=true >/dev/null 2>&1
  sleep 8
done
