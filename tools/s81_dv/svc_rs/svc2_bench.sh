#!/usr/bin/env bash
# SVC2 (10-19): dsdv_svc_rs 16-slice exact bench on the SRAM attention share (OT_SVC_LAND_SRAM + OT_SVC_ATT_SRAM [+ PINREG]).
# Usage (repo root): svc2_bench.sh OUT VARIANT ST PMEM_E PIN(0|1) CASE...   (vectors: results/rtl/s81_dv_1016/svc_rs/svc2_1019/vec.tar,
#   the 4 golden cases full1m short300 skew1m tail46 of the S81-CTRL-SVC 023389fd2 bench; 2 seeds each)
# Prints one line per run and a final "SVC2_BENCH <variant> PASS|FAIL runs=N fail=F".
set -uo pipefail
O=$1; V=$2; ST=$3; PE=$4; PIN=$5; shift 5
mkdir -p "$O"; [ -d "$O/vec" ] || tar xf results/rtl/s81_dv_1016/svc_rs/svc2_1019/vec.tar -C "$O" || exit 1
X="OT_SVC_LAND_SRAM OT_SVC_ATT_SRAM"; [ "$PIN" = 1 ] && X="$X OT_SVC_ATT_PINREG"
export DIE=0 ST PMEM_E=$PE JOBS=${JOBS:-6} RS_XDEF="$X" MAXCYC=${MAXCYC:-40000}
${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator} --version
tools/s81_dv/svc_rs/rs_bench_pl.sh "$O/out" "$O/vec" "$V" || { echo "SVC2_BENCH $V BUILD FAIL"; exit 1; }
for C in "$@"; do for s in 1 2; do
  SEEDS=$s tools/s81_dv/svc_rs/rs_bench_pl.sh "$O/out" "$O/vec" "$V" "$C" > "$O/v_${V}_${C}_$s.txt" 2>&1 &
done; done; wait
cat "$O"/v_${V}_*.txt; n=$(cat "$O"/v_${V}_*.txt | grep -c "verdict="); f=$(cat "$O"/v_${V}_*.txt | grep -c "verdict=PASS" ); f=$((n - f))
[ "$n" -gt 0 ] && [ "$f" = 0 ] && echo "SVC2_BENCH $V PASS runs=$n fail=0" || echo "SVC2_BENCH $V FAIL runs=$n fail=$f"
