#!/usr/bin/env bash
# TOK-FUNC-HBM-PAY (10-21): run replay mem dirs on an ALREADY BUILT slice binary (tok_func_hbm.sh step 4 form), unpinned
# ot-run on the build host (--dir = the build's obj dir exists only there), collect SLICE_PASS/FAIL + SLICE_SUMMARY.
#   REMOTE=<bundle root on the build host, holding out/obj/Vtb_hbm_slice + check_slice_run.py>  RDIR=<replay dir rel. to
#   REMOTE, e.g. slice/replay_pay>  HOST=<build host>  OUT=<local result dir>  [PAR=8]  names... (default: all in RDIR)
set -u
REMOTE=${REMOTE:?}; RDIR=${RDIR:?}; HOST=${HOST:?}; OUT=${OUT:?}; PAR=${PAR:-8}
mkdir -p "$OUT/log"
NAMES=("$@"); [ ${#NAMES[@]} -eq 0 ] && NAMES=($(timeout 120 ssh "$HOST" "ls $REMOTE/$RDIR"))
run1() {
  n=$1
  /home/ubuntu/bin/ot-run --mem "${RUN_MEM:-32}" --threads 1 --dir "$REMOTE/out/obj" -- bash -c "cd $REMOTE && mkdir -p out_pay/$n && /usr/bin/time -v -o out_pay/$n/run.time out/obj/Vtb_hbm_slice +verilator+rand+reset+0 +REPLAY=$RDIR/$n > out_pay/$n/run.log 2>&1; echo RUN_RC=\$?; python3 check_slice_run.py --replay $RDIR/$n --run-log out_pay/$n/run.log --out out_pay/$n/acceptance.json >/dev/null 2>&1; grep -E '^SLICE_(SUMMARY|PASS|FAIL)' out_pay/$n/run.log | tail -2" > "$OUT/log/$n.log" 2>&1
  echo "$(date -Is) RUN $n $(grep -E 'RUN_RC|^SLICE_' "$OUT/log/$n.log" | tr '\n' ' ')" >> "$OUT/summary.log"
  timeout 300 rsync -a "$HOST:$REMOTE/out_pay/$n/" "$OUT/runs/$n/" 2>/dev/null
}
i=0
for n in "${NAMES[@]}"; do run1 "$n" & i=$((i+1)); [ $((i % PAR)) -eq 0 ] && wait; sleep 1; done
wait
echo "$(date -Is) ALL_DONE ${#NAMES[@]}" >> "$OUT/summary.log"
