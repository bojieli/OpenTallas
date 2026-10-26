#!/usr/bin/env bash
# Root cut only: all production ports and CB21 parameters, no 32-tile C++ build.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
SELF="$ROOT/tools/hbm_b2/tkm_l74"
OUT=$(realpath -m "${1:?output directory}")
mkdir -p "$OUT"
python3 "$SELF/rootpipe_probe_sources.py" --out "$OUT"
cd "$ROOT"
src=("$SELF/tb_rootpipe_lockstep.sv" "$OUT/root_p.sv" "$OUT/root_pd.sv" rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_buffer.sv rtl/lib/ot_rst_relay.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
for bdr in 0 1; do
 iverilog -g2012 -s tb -Ptb.BDR=$bdr -o "$OUT/probe_$bdr" "${src[@]}" > "$OUT/build_$bdr.log" 2>&1
 vvp "$OUT/probe_$bdr" | tee "$OUT/positive_$bdr.log"
done
iverilog -g2012 -s tb -Ptb.MUT=1 -Ptb.BDR=1 -o "$OUT/mutant" "${src[@]}" > "$OUT/mutant_build.log" 2>&1
if vvp "$OUT/mutant" > "$OUT/mutant.log" 2>&1; then
 echo 'ROOTPIPE_MUTANT_SURVIVED' >&2
 exit 1
fi
grep -F 'ROOTPIPE_LOCKSTEP FAIL' "$OUT/mutant.log"
python3 "$SELF/rootpipe_probe_sources.py" --out "$OUT/sortmut" --mutant-sort
src[2]="$OUT/sortmut/root_pd.sv"
iverilog -g2012 -s tb -Ptb.BDR=1 -o "$OUT/sortmutant" "${src[@]}" > "$OUT/sortmutant_build.log" 2>&1
if vvp "$OUT/sortmutant" > "$OUT/sortmutant.log" 2>&1; then
 echo 'ROOTPIPE_STABLE_SORT_MUTANT_SURVIVED' >&2
 exit 1
fi
grep -F 'ROOTPIPE_LOCKSTEP FAIL' "$OUT/sortmutant.log"
echo 'ROOTPIPE_ROOT_CUT_GATE_PASS: shift0, MUTP1 and stable-sort mutant caught, data-cycle delta0'
