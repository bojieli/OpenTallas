#!/bin/bash
# HBM-NEXT-SM4 leaf bench on Verilator 5.050 (the closure daemon's version), on the FLEET only.
#   run_leaf_bench.sh OUT P MUT [THR] [extra -G...]
# MUT=0 THR=0: prints "PASS HNX-RP4LP4"; MUT 1/2/3 must FAIL with "LANE MISMATCH" (1, 2) / "STREAM MISMATCH" (3).
set -u
OUT=$1; P=$2; MUT=$3; THR=${4:-0}; shift; shift; shift; [ $# -gt 0 ] && shift; EXTRA="$*"
R=$(cd "$(dirname "$0")/../../../.." && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$R"
S=$(python3 -c "import json;print(' '.join(json.load(open('rtl/hbm_next/sm/sources.json'))['sim_sources']))")
D=$(python3 -c "import json;print(' '.join('-D'+d for d in json.load(open('rtl/hbm_next/sm/sources.json'))['defines']))")
TAG=p${P}_m${MUT}_t${THR}; B=$OUT/build_$TAG; mkdir -p "$B"
"$VL" --version > "$OUT/verilator_$TAG.version"
build() { "$VL" --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hnx_rp4lp4_leaf -GP=$P -GMUT=$MUT -GTHR=$THR $EXTRA \
  --Mdir "$B" -j ${VL_JOBS:-8} $D $S rtl/hbm_next/sm/tb/tb_hnx_rp4lp4_leaf.sv > "$OUT/build_$TAG.log" 2>&1; }
build || { echo "retry once (PCH race)"; rm -rf "$B"; mkdir -p "$B"; build; } || { echo "BUILD FAIL $TAG"; tail -20 "$OUT/build_$TAG.log"; exit 3; }
"$B/Vtb_hnx_rp4lp4_leaf" +seed=${SEED:-7} > "$OUT/run_$TAG.log" 2>&1; rc=$?
grep -E 'HNX_RP4LP4|lane [0-9]|THROUGHPUT|PASS|FAIL|MISMATCH' "$OUT/run_$TAG.log" | head -20
rm -rf "$B"
if [ "$MUT" = 0 ]; then grep -q 'PASS HNX-RP4LP4' "$OUT/run_$TAG.log" && [ $rc = 0 ] && echo "BENCH PASS $TAG" && exit 0
else [ $rc != 0 ] && grep -q 'MISMATCH' "$OUT/run_$TAG.log" && echo "MUTANT CAUGHT $TAG" && exit 0; fi
echo "BENCH FAIL $TAG rc=$rc"; exit 1
