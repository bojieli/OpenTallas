#!/bin/bash
# KV-P2-RTL 10-23: run.sh case list of tools/qwen_layerbench/kvattn_rel (bench 0e597ed1c) with FD FORCED (no calibration).
# Usage: runfd.sh BIN VECDIR OUTDIR FD
set -uo pipefail
B=$(realpath "$1"); V=$(realpath "$2"); O=$(realpath -m "$3"); FD=$4; mkdir -p "$O/runs"
run() { local name=$1; shift; local D=$O/runs/$name; mkdir -p "$D"
  ( /usr/bin/time -f "%e s %M KB" -o "$D/time" "$B" "$@" > "$D/sim.log" 2>&1; echo $? > "$D/exit" ) ; }
run cal_T1024 +NU=1 +CTX=1024 +FD=$FD +VEC0=$V/T1024_s1 &
for T in 1024 4096 8192; do
  run u1_T$T +NU=1 +CTX=$T +FD=$FD +VEC0=$V/T${T}_s1 &
  run u4_T$T +NU=4 +CTX=$T +FD=$FD +VEC0=$V/T${T}_s1 +VEC1=$V/T${T}_s2 +VEC2=$V/T${T}_s3 +VEC3=$V/T${T}_s4 &
done
run u1_T4096_peaky +NU=1 +CTX=4096 +FD=$FD +VEC0=$V/T4096_peaky &
run u1_T8191 +NU=1 +CTX=8191 +FD=$FD +VEC0=$V/T8191_s6 &
run u1_T32768_bound +NU=1 +CTX=32768 +FD=$FD +VEC0=$V/T8192_s1 &
for m in k_shift v_swap q_swap k_late; do run mut_$m +NU=1 +CTX=1024 +FD=$FD +VEC0=$V/T1024_s1 +MODE=$m & done
for g in 1 2 4; do run mut_gmut$g +NU=1 +CTX=1024 +FD=$FD +VEC0=$V/T1024_s1 +GMUT=$g & done
wait
l=$(grep -m1 '^FIN0' "$O/runs/cal_T1024/sim.log" || true)
if [ -n "$l" ]; then a=$(echo "$l" | sed -E 's/.*root age ([0-9]+) face res_t ([0-9]+).*/\1 \2/'); fa=${a% *}; rt=${a#* }
  echo "FD_forced=$FD FD_calibrated=$(( FD + fa - (rt - 1) )) ($l)" > "$O/fd.txt"; else echo "FD_forced=$FD no FIN0" > "$O/fd.txt"; fi
for d in "$O"/runs/*/; do echo "$(basename $d) exit=$(cat $d/exit) $(grep '^KVATTN_REL' $d/sim.log)"; done > "$O/summary.txt"
cat "$O/fd.txt" "$O/summary.txt"; echo RUN_DONE
