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
 '# HBMc/TOKEN 10-22: the TB default CYCLES = last STREAM event + 64 ignores serial/hbm-domain events, so a replay whose' \
 '# events are mostly serial/hbm stops early (qw_chain_r0: 173 of ~66.7k stream cycles, 18/9826 drives, 0 checks; RoPE 133).' \
 '# Run to the last event of EVERY domain in stream edges (measured edge ratios stream:serial 1.3334, stream:hbm 1.2288).' \
 'C=$(python3 - "$2/$n/hdr.mem" "${CYC_SERIAL_RATIO:-1.3334}" "${CYC_HBM_RATIO:-1.2288}" <<"PY"' \
 'import math, sys' \
 'last = [0, 0, 0, 0]' \
 'for h in open(sys.argv[1]).read().split():' \
 '    x = int(h, 16)' \
 '    if (x >> 62) != 3: last[(x >> 60) & 3] = max(last[(x >> 60) & 3], x & 0xFFFFFFFF)' \
 'print(math.ceil(max(last[0], last[1] * float(sys.argv[2]), last[2] * float(sys.argv[3])) * 1.01) + 256)' \
 'PY' \
 ')' \
 '[ -n "$C" ] || exit 2' \
 'echo "CYCLES=$C"' \
 'out/obj/Vtb_hbm_slice +verilator+rand+reset+0 "+REPLAY=$2/$n" "${H[@]}" "+CYCLES=$C" > "out_pay/$n/run.log" 2>&1' \
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
