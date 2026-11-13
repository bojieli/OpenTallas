#!/bin/bash
# revert a type to stage1 whenever collector_reattach names its source as unreachable; repeat
set -uo pipefail; cd /
W=/srv/opentallas-scratch2/claude/qc-s28b
cp ${PIN:-$W/planq/s28b2_pin.json} $W/planq/s28b2_loop.json
: > $W/reattach_reverted.txt
for i in $(seq 1 15); do
  cd $W/srcB && nice -n 19 python3 -I -B tools/die_plan/collector_reattach.py $W/planq/s28b_stage1.json $W/planq/s28b2_loop.json $W/planq/${OUTP:-s28b2}.json $W/reattach_${OUTP:-s28b2}.json --sidecar $W/sidecar_s28.json $W/sidecar_${OUTP:-s28b2}.json > $W/reattach_s28b2.log 2>&1
  rc=$?; echo "iter $i rc=$rc $(tail -c 300 $W/reattach_s28b2.log | tr '\n' ' ' | cut -c1-250)"
  [ $rc = 0 ] && break
  src=$(grep -o "collector source [^:]*" $W/reattach_s28b2.log | tail -1 | awk '{print $3}')
  [ -z "$src" ] && { echo "no source named"; break; }
  cd $W && python3 -I - "$src" <<'PY'
import json, sys
W = "/srv/opentallas-scratch2/claude/qc-s28b/planq/"
a = json.load(open(W + "s28b_stage1.json"))["partition_types"]; P = json.load(open(W + "s28b2_loop.json")); b = P["partition_types"]
hit = [t for t in b if a[t] != b[t] and any(s.get("name") == sys.argv[1] for s in
       (b[t].get("clock", {}).get("landing_contract", {}).get("collector_local_sources") or []) +
       (b[t].get("clock", {}).get("landing_contract", {}).get("collector_children") or []))]
for t in hit:
    b[t] = a[t]
open(W + "s28b2_loop.json", "w").write(json.dumps(P, indent=1) + "\n")
open("/srv/opentallas-scratch2/claude/qc-s28b/reattach_reverted.txt", "a").write(" ".join(hit) + f" ({sys.argv[1]})\n")
print("reverted", hit)
PY
done
