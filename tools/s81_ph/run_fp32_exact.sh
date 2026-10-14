#!/bin/bash
set -euo pipefail
TREE=$1
RUN=$2
mkdir -p "$RUN"
python3 "$TREE/tools/s81_ph/fp32_add_exact_reference.py" "$RUN" --tree "$TREE" --n 100000 > "$RUN/generate.log"
NVALID=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["valid_vectors"])' "$RUN/reference.json")
sha256sum "$TREE/tools/s81_ph/fp32_add_exact_reference.py" "$TREE/rtl/dsrom_sys/s81_ph/test/tb_s81ph_fp32_exact.sv" "$TREE/rtl/gpu/ot_fp32_add_rne_deep.sv" "$TREE/rtl/hdc/ot_hdc_prefix.sv" > "$RUN/sources.sha256"
iverilog -g2012 -s tb_s81ph_fp32_exact -o "$RUN/positive" "$TREE/rtl/gpu/ot_fp32_add_rne_deep.sv" "$TREE/rtl/hdc/ot_hdc_prefix.sv" "$TREE/rtl/dsrom_sys/s81_ph/test/tb_s81ph_fp32_exact.sv" > "$RUN/build_positive.log" 2>&1
vvp "$RUN/positive" +VECTORS="$RUN/vectors.txt" +NVALID="$NVALID" > "$RUN/run_positive.log" 2>&1
grep 'FP32_EXACT_GATE PASS' "$RUN/run_positive.log"
iverilog -g2012 -s tb_s81ph_fp32_exact -o "$RUN/mutant" "$RUN/deep_rne_tie_away_mutant.sv" "$TREE/rtl/hdc/ot_hdc_prefix.sv" "$TREE/rtl/dsrom_sys/s81_ph/test/tb_s81ph_fp32_exact.sv" > "$RUN/build_mutant.log" 2>&1
if vvp "$RUN/mutant" +VECTORS="$RUN/vectors.txt" +NVALID="$NVALID" > "$RUN/run_mutant.log" 2>&1;then echo 'FP32_ARITH_RNE_MUTANT NOT_DETECTED';exit 1;fi
grep 'FP32 independent reference mismatch' "$RUN/run_mutant.log"
echo 'FP32_ARITH_RNE_MUTANT FAIL_AS_REQUIRED'
