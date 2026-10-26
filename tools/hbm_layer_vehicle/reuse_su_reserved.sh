#!/usr/bin/env bash
# Reuse the immutable r14 NEV11633 binary with separately staged reserved probes.
# No source, TB, original replay or original run output is modified.
set -u -o pipefail
REMOTE=${REMOTE:-/srv/opentallas-scratch/claude/tok-func-hbm/r14sw}
HOST=${HOST:-ot-gold1} # read-only locality probe, execution uses unpinned ot-run
OUT=${OUT:?OUT}
mkdir -p "$OUT/log"
while ! timeout 30 ssh "$HOST" "test -x $REMOTE/out/obj/Vtb_hbm_slice"; do
  echo "$(date -Is) waiting for preserved r14 binary" >> "$OUT/log/wait.log"
  sleep 60
done
rc=0
for name in ds_l0 ds_l2 ds_l14 qw_l0_r0 qw_l0_r5 qw_chain_r0 qw_chain_r5; do
  /home/ubuntu/bin/ot-run --mem 64 --threads 1 --dir "$REMOTE/out/obj" -- bash -c '
    cd "$1" || exit 2
    mkdir -p "out_reserved11633_$2"
    out/obj/Vtb_hbm_slice +verilator+rand+reset+0 "+REPLAY=replay_reserved11633/$2" > "out_reserved11633_$2/run.log" 2>&1
    simrc=$?
    python3 check_slice_run.py --replay "replay_reserved11633/$2" --run-log "out_reserved11633_$2/run.log" --out "out_reserved11633_$2/acceptance.json"
    checkrc=$?
    test "$simrc" = 0 && test "$checkrc" = 0
  ' _ "$REMOTE" "$name" > "$OUT/log/$name.log" 2>&1 || rc=1
  timeout 120 rsync -a "$HOST:$REMOTE/out_reserved11633_$name/" "$OUT/runs/$name/" || rc=1
done
echo "$(date -Is) reserved_component_replay_rc=$rc" >> "$OUT/log/wait.log"
exit "$rc"
