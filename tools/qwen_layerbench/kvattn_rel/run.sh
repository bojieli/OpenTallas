#!/bin/bash
# TOKSIM-KVATTN 2026-10-19: vectors (CPU golden) + the measured runs of the release attention vehicle.
# Usage: run.sh SRC_ROOT OUT_DIR   (OUT_DIR holds obj/Vtb_kvattn_rel from build.sh)
#   1 user and 4 users at T = 1024 / 4096 / 8192 (golden seeds 1..4, kind normal) + T4096 kind peaky (1 user),
#   T = 32768 (release RTL bound check: expected REFUSED), and 7 mutants at T1024 (each must FAIL).
set -uo pipefail
R=$(realpath "$1"); O=$(realpath -m "$2"); B=$O/obj/Vtb_kvattn_rel; V=$O/vec; mkdir -p "$V" "$O/runs"
cd "$R"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2
for T in 1024 4096 8192; do for s in 1 2 3 4; do
  python3 tools/qwen_tp8_attention_native.py vectors --ctx $T --seed $s --out "$V/T${T}_s$s" > "$V/T${T}_s$s.log" 2>&1 &
done; done
python3 tools/qwen_tp8_attention_native.py vectors --ctx 4096 --seed 5 --kind peaky --out "$V/T4096_peaky" > "$V/T4096_peaky.log" 2>&1 &
wait
for d in "$V"/T*/; do test -s "$d/gold.hex" || { echo "VECTORS FAIL $d"; exit 1; }; done
sha256sum "$V"/*/*.hex "$V"/*/meta.json > "$O/vectors.sha256"
run() { local name=$1; shift; local D=$O/runs/$name; mkdir -p "$D"
  ( /usr/bin/time -f "%e s %M KB" -o "$D/time" "$B" "$@" > "$D/sim.log" 2>&1; echo $? > "$D/exit" ) ; }
# FD calibration on T1024 (fin pin must reach the face one edge before res_t); FD = the vehicle's compiled F_DLY
FD=3
run cal_T1024 +NU=1 +CTX=1024 +FD=$FD +VEC0=$V/T1024_s1
l=$(grep -m1 '^FIN0' "$O/runs/cal_T1024/sim.log" || true)
if [ -n "$l" ]; then a=$(echo "$l" | sed -E 's/.*root age ([0-9]+) face res_t ([0-9]+).*/\1 \2/'); fa=${a% *}; rt=${a#* }
  FD=$(( FD + fa - (rt - 1) )); fi
echo "FD=$FD (calibration: $l)" > "$O/fd.txt"
for T in 1024 4096 8192; do
  run u1_T$T +NU=1 +CTX=$T +FD=$FD +VEC0=$V/T${T}_s1 &
  run u4_T$T +NU=4 +CTX=$T +FD=$FD +VEC0=$V/T${T}_s1 +VEC1=$V/T${T}_s2 +VEC2=$V/T${T}_s3 +VEC3=$V/T${T}_s4 &
done
run u1_T4096_peaky +NU=1 +CTX=4096 +FD=$FD +VEC0=$V/T4096_peaky &
run u1_T32768_bound +NU=1 +CTX=32768 +FD=$FD +VEC0=$V/T8192_s1 &
for m in k_shift v_swap q_swap k_late; do run mut_$m +NU=1 +CTX=1024 +FD=$FD +VEC0=$V/T1024_s1 +MODE=$m & done
for g in 1 2 4; do run mut_gmut$g +NU=1 +CTX=1024 +FD=$FD +VEC0=$V/T1024_s1 +GMUT=$g & done
wait
for d in "$O"/runs/*/; do echo "$(basename $d) exit=$(cat $d/exit) $(grep '^KVATTN_REL' $d/sim.log)"; done > "$O/summary.txt"
cat "$O/summary.txt"
echo RUN_DONE
