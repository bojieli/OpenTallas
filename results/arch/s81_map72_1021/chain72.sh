#!/bin/bash
# Keep probe -> actual allocator map -> six exact chunks moving without a new
# consumer bench or physical audit. Coordinator-side orchestration only.
set -uo pipefail
L=/srv/opentallas-scratch/claude/codex-s81-map72-1021
OTR=/home/ubuntu/bin/ot-run
TAG=f72r224gpq
run() { "$OTR" --mem "$1" --threads "$2" --dir "$L" -- "${@:3}"; }
log() { echo "[$(date -Is)] $TAG $*"; }
until ssh ot-epyc9 "grep -q PROBE_RC $L/probe_$TAG.log" 2>/dev/null; do sleep 30; done
log 'probe terminal'
if ! ssh ot-epyc9 "grep -q '^PROBE_RC 0$' $L/probe_$TAG.log"; then log 'PROBE FAILED'; exit 1; fi
N=min
for attempt in 1 2; do
  result=$(run 8 2 bash -c "cd $L && PYTHONDONTWRITEBYTECODE=1 OT_XS_TOPO=1 OT_XS_PROP=1 python3 mk_map.py out/probe_$TAG/summary.json 224 $TAG $N 6" 2>&1)
  echo "$result"
  record=$(echo "$result" | grep '^DENSE2_MAP ')
  [ -n "$record" ] || { log 'MAP FAILED'; exit 1; }
  N=$(echo "$record" | python3 -c "import sys,json; print(json.loads(sys.stdin.read().split(' ',1)[1])['stages'])")
  pids=()
  for k in 0 1 2 3 4 5; do
    run 48 16 bash run72.sh "specs_${TAG}_${N}_c$k.json" "${TAG}_${N}_c$k" > "/home/ubuntu/scratch/codex-s81-map72-1021/exact_${N}_c$k.otrun.log" 2>&1 &
    pids+=("$!")
  done
  for pid in "${pids[@]}"; do wait "$pid"; done
  log "exact chunks terminal N=$N"
  result=$(run 8 2 bash -c "cd $L && export PYTHONDONTWRITEBYTECODE=1 OT_XS_TOPO=1 OT_XS_PROP=1; python3 root/tools/s81_dv/layer_prog/xs_stage_map.py merge --map stage_map_${TAG}_${N}.json --runs out/${TAG}_${N}_c*/summary.json && python3 root/tools/s81_dv/layer_prog/xs_stage_map.py table --map stage_map_${TAG}_${N}.json > stage_table_${TAG}_${N}.md && python3 qualify_price.py stage_map_${TAG}_${N}.json 72 > qualify_${TAG}_${N}.log 2>&1; tail -c 600 qualify_${TAG}_${N}.log" 2>&1)
  echo "$result"
  if echo "$result" | grep -q '"verdict": "PASS"'; then log "PASS $N (capacity only; MU calendar owed)"; exit 0; fi
  N=$((N+4))
done
log 'FAIL after one N+4 rebuild'
exit 2
