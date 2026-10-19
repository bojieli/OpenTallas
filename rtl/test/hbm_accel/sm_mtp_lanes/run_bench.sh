#!/bin/bash
# Lane-equivalence bench on Verilator 5.050 (the closure daemon's version).  Usage: run_bench.sh OUT P MUT [SEED]
# PASS (MUT=0): prints "PASS P-LANE"; negative control (MUT=1): must fail with "LANE MISMATCH".
set -u
OUT=$1; P=$2; MUT=$3; SEED=${4:-7}
R=$(cd "$(dirname "$0")/../../../.." && pwd)
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
S=$(python3 -c "import json;print(' '.join(json.load(open('$R/physical/ref_tile/smh_bdc_ref_p50/spec.json'))['sources']))")
D=$(python3 -c "import json;print(' '.join('-D'+d for d in json.load(open('$R/physical/ref_tile/smh_bdc_ref_p50/spec.json'))['defines']))")
B=$OUT/build_p${P}_m${MUT}; mkdir -p "$B"
cd "$R"
"$VL" --version > "$OUT/verilator_p${P}_m${MUT}.version"
"$VL" --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style --top-module tb_hbm_sm_bdc_p -GP=$P -GMUT=$MUT --Mdir "$B" -j 8 \
  $D $S rtl/hbm_accel/sm/mtp_lanes/ot_hbm_sm_bdc_p.sv rtl/test/hbm_accel/sm_mtp_lanes/tb_hbm_sm_bdc_p.sv \
  > "$OUT/build_p${P}_m${MUT}.log" 2>&1 || { echo "BUILD FAIL P=$P MUT=$MUT"; exit 3; }
"$B/Vtb_hbm_sm_bdc_p" +seed=$SEED > "$OUT/run_p${P}_m${MUT}.log" 2>&1; rc=$?
tail -3 "$OUT/run_p${P}_m${MUT}.log"
if [ "$MUT" = 0 ]; then grep -q 'PASS P-LANE' "$OUT/run_p${P}_m${MUT}.log" && [ $rc = 0 ] && echo "BENCH PASS P=$P" && exit 0
else [ $rc != 0 ] && grep -q 'LANE MISMATCH' "$OUT/run_p${P}_m${MUT}.log" && echo "MUTANT CAUGHT P=$P MUT=$MUT" && exit 0; fi
echo "BENCH FAIL P=$P MUT=$MUT rc=$rc"; exit 1
