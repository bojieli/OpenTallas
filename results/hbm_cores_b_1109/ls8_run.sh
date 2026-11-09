#!/usr/bin/env bash
# S81-SVC-6: H8 R5 whole-slice lock-step (16 real slices) on codex/svc-rtl-1113@750f6bffd5 (P-source fix b1275c27ba).
# Same images as the failed S81-SVC-5 run s81-svc-5/ls (only the RTL changed); controls hb_swap, more_off, pass_drop, pass_swap.
set -uo pipefail
S=/srv/opentallas-scratch3/claude/s81-svc-6
cd "$S/src"
O=$S/ls8
echo "start $(date) host $(hostname)"
JOBS=16 bash tools/s81_dv/layer_prog/svc/build_ls.sh "$O" 8 || { echo BUILD_FAIL; exit 1; }
V=$O/obj/Vtb_svc_lockstep
run() { # name seed
  local n=$1 s=$2
  "$V" +dir="$S/img/h8/$n" +seed=$s > "$O/run_${n}_s$s.log" 2>&1
  echo "$n s$s rc=$? $(grep -h '^LS_END' "$O/run_${n}_s$s.log" | tail -1)"
}
run base 1 & run base 2 &
run hb_swap 1 & run more_off 1 & run pass_drop 1 & run pass_swap 1 &
wait
C="python3 -I tools/s81_dv/layer_prog/svc/check_lockstep.py ."
H16="$S/img/h16/base $S/img/h16/base/ls_dump_h16_s1.txt"
rc=0
for t in base:1 base:2 hb_swap:1 more_off:1 pass_drop:1 pass_swap:1; do
  n=${t%:*}; s=${t#*:}
  $C $H16 "$S/img/h8/$n" "$S/img/h8/$n/ls_dump_h8_s$s.txt" --out "$O/check_${n}_s$s.json" > "$O/check_${n}_s$s.log" 2>&1
  r=$?
  echo "$n s$s check rc=$r $(tail -n 1 "$O/check_${n}_s$s.log" | cut -c1-200)"
done
echo "done $(date)"
