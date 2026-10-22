#!/usr/bin/env bash
# Replay existing slice binaries through unpinned ot-run. Every simulation and
# acceptance exit is preserved; staged shell variables survive systemd quoting.
set -uo pipefail
REMOTE=${REMOTE:?}; RDIR=${RDIR:?}; HOST=${HOST:?}; OUT=${OUT:?}; PAR=${PAR:-8}
mkdir -p "$OUT/log" "$OUT/runs"
NAMES=("$@"); if [ ${#NAMES[@]} -eq 0 ]; then
  inventory=$(timeout 120 ssh "$HOST" "ls $REMOTE/$RDIR") || exit 2
  [ -n "$inventory" ] || exit 2
  mapfile -t NAMES <<< "$inventory"
fi
printf '%s\n' '#!/usr/bin/env bash' 'set -uo pipefail' \
 'cd "$1" || exit 2' 'n=$3; mkdir -p "out_pay/$n"' \
 'H=(); [ -d "$2/$n/hbm" ] && H=("+HBM_IMG_DIR=$2/$n/hbm")' \
 'out/obj/Vtb_hbm_slice +verilator+rand+reset+0 "+REPLAY=$2/$n" "${H[@]}" > "out_pay/$n/run.log" 2>&1' \
 'simrc=$?' \
 'python3 check_slice_run.py --replay "$2/$n" --run-log "out_pay/$n/run.log" --boundary slice/boundary.json --tb-source slice/tb_slice.sv --out "out_pay/$n/acceptance.json"' \
 'checkrc=$?' 'echo "RUN_RC=$simrc CHECK_RC=$checkrc"' \
 'test "$simrc" = 0 && test "$checkrc" = 0' \
 | timeout 120 ssh "$HOST" "cat > $REMOTE/run_one_pay_safe.sh" || exit 2
run1() {
  local n=$1 rc=0
  /home/ubuntu/bin/ot-run --mem "${RUN_MEM:-64}" --threads 1 --dir "$REMOTE/out/obj" -- \
    bash "$REMOTE/run_one_pay_safe.sh" "$REMOTE" "$RDIR" "$n" > "$OUT/log/rpl_$n.log" 2>&1 || rc=1
  timeout 120 rsync -a "$HOST:$REMOTE/out_pay/$n/" "$OUT/runs/$n/" || rc=1
  echo "$(date -Is) RUN $n rc=$rc" >> "$OUT/pay_summary.log"
  return "$rc"
}
status=0; pids=()
for n in "${NAMES[@]}"; do
  [[ "$n" =~ ^[a-zA-Z0-9_.-]+$ ]] || exit 2
  run1 "$n" & pids+=("$!")
  if [ ${#pids[@]} -ge "$PAR" ]; then
    for pid in "${pids[@]}"; do wait "$pid" || status=1; done
    pids=()
  fi
done
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
echo "$(date -Is) ALL_DONE ${#NAMES[@]} rc=$status" >> "$OUT/pay_summary.log"
exit "$status"
