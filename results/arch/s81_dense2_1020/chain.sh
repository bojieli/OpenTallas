#!/bin/bash
# DENSE2 10-20 chain (runs on the coordinator host; every heavy step via ot-run in the ep9 lane root):
#   wait probe -> mk_map (min stages from the ACTUAL probe costs) -> K exact chunks in parallel -> merge -> table ->
#   qualify+price; if any stage fails the exact gate, rebuild at N+4 once.
# usage: chain.sh TAG DROPFC R CT GP [K]      e.g. chain.sh f98r224 3R,4L 224 0 0 8
set -uo pipefail
TAG=$1 DROP=$2 R=$3 CT=$4 GP=$5 K=${6:-8}
L=/srv/opentallas-scratch/claude/s81-dense2-1020; OTR=/home/ubuntu/bin/ot-run
FR=$( [ "$DROP" = "3R,4L" ] && echo 98 || echo 84 )
run() { $OTR --mem "$1" --threads "$2" --dir $L -- "${@:3}"; }
log() { echo "[$(date +%H:%M:%S)] $TAG $*"; }
until ssh ot-epyc9 "grep -q PROBE_RC $L/probe_$TAG.log" 2>/dev/null; do sleep 120; done
log probe done
N=min
for attempt in 1 2; do
  out=$(run 8 2 bash -c "cd $L && PYTHONDONTWRITEBYTECODE=1 OT_XS_TOPO=1 OT_XS_PROP=1 python3 mk_map.py out/probe_$TAG/summary.json $R $TAG $N $K" 2>&1 | grep DENSE2_MAP)
  log "$out"; [ -n "$out" ] || { log MAPFAIL; exit 1; }
  N=$(echo "$out" | python3 -c "import sys,json; print(json.loads(sys.stdin.read().split(' ',1)[1])['stages'])")
  pids=()
  for k in $(seq 0 $((K-1))); do
    run 48 16 ./run_cap.sh $DROP 1 specs_${TAG}_${N}_c$k.json ${TAG}_${N}_c$k $CT $GP > /tmp/dense2_${TAG}_${N}_c$k.otrun.log 2>&1 & pids+=($!)
  done
  for p in "${pids[@]}"; do wait $p; done
  log exact chunks done
  res=$(run 8 2 bash -c "cd $L && export PYTHONDONTWRITEBYTECODE=1 OT_XS_TOPO=1 OT_XS_PROP=1; python3 root/tools/s81_dv/layer_prog/xs_stage_map.py merge --map stage_map_${TAG}_${N}.json --runs out/${TAG}_${N}_c*/summary.json; python3 root/tools/s81_dv/layer_prog/xs_stage_map.py table --map stage_map_${TAG}_${N}.json > stage_table_${TAG}_${N}.md; python3 qualify_price.py stage_map_${TAG}_${N}.json $FR > qualify_${TAG}_${N}.log 2>&1; tail -c 600 qualify_${TAG}_${N}.log" 2>&1 | grep -v '^ot-')
  log "$res"
  echo "$res" | grep -q '"verdict": "PASS"' && { log PASS $N; exit 0; }
  N=$((N+4))
done
log FAIL after rebuild
exit 2
