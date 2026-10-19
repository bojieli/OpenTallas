#!/usr/bin/env bash
# HF-5c 10-18: random lockstep ot_hbm_accel_smh_attn (generate form) vs ot_hbm_accel_smh_attn_flat (wires-only flat form).
# Run on the FLEET (ot-run), never on localhost.  usage: hf5c_flat_eq.sh EMUT OUTDIR   (EMUT 0 must PASS, 1 / 2 must FAIL)
# Every file the bench reads: SRC below (sm_elem_bench.py's list + the flat parent + its split-front children + the tb).
set -u
cd "${LP_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
M=$1; OUT=$2; mkdir -p "$OUT"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
SRC=$(python3 -c "import re;t=open('tools/hbm_sm_attention/sm_elem_bench.py').read();print(' '.join(s for s in re.findall(r'\"([^\"]+)\"',re.search(r'SRC = \[(.*?)\]',t,re.S).group(1)) if not s.startswith('rtl/test/')))")
SRC="$SRC rtl/hbm_accel/sm/attn/flat/ot_hbm_sm_attn_front_split.sv rtl/hbm_accel/sm/attn/flat/ot_hbm_accel_smh_attn_flat.sv rtl/test/hbm_accel/sm_attn/tb_smh_attn_flat_eq.sv"
$VL --version > "$OUT/eq$M.version"
$VL --binary -j ${VJOBS:-16} -O1 -CFLAGS -O1 --x-assign 0 --x-initial 0 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
    -Wno-MULTIDRIVEN --unroll-count 256 --top-module tb_smh_attn_flat_eq -DOT_SMH_HIER -DOT_SMH_FC_HIER -GEMUT=$M \
    --Mdir "$OUT/obj_eq$M" $SRC > "$OUT/build_eq$M.log" 2>&1 || { echo "BUILD FAIL (see $OUT/build_eq$M.log)"; exit 2; }
"$OUT/obj_eq$M/Vtb_smh_attn_flat_eq" > "$OUT/eq$M.log" 2>&1
r=$(grep -o 'FLAT_EQ [A-Z]*' "$OUT/eq$M.log" | head -1)
echo "EMUT $M: ${r:-NO_RESULT}"; grep -m1 FLAT_EQ "$OUT/eq$M.log"
if [ "$M" -eq 0 ]; then [ "$r" = "FLAT_EQ PASS" ]; else [ "$r" = "FLAT_EQ FAIL" ]; fi
