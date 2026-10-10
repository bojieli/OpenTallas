#!/bin/bash
# cont-takeover 2026-10-09: NK4 registered score slice stream-equivalence bench.  idx_bench.sh pos|neg <workdir>
# pos: IDXB_PASS (rc 0) when the wrapper's score stream equals the bare full-geometry slice's; neg (+MUT key-lane swap):
# IDXB_NEG_FAIL (rc 1) when the mismatch is caught.
set -u
M=$1; W=$2; mkdir -p "$W"; W=$(cd "$W" && pwd)
V=rtl/hdc/v41x; H=rtl/hdc
S="$V/ot_hdc_v41x_idx_lat.sv $V/ot_hdc_v41x_idx_arith_lat.sv $V/ot_hdc_v41x_idx_arith.sv $H/ot_hdc_delay.sv $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv $V/ot_hdc_v41x_idx_score_slice_reg.sv rtl/test/tb_idx_slice_reg_equiv.sv"
# Verilator (Icarus spent > 1.7 h elaborating the 512-dot slice twice without finishing)
VL=$(command -v verilator || echo $HOME/.local/opentallas-tools/verilator-5.050/bin/verilator)
$VL --binary --timing -O2 -j 16 -Wno-fatal -Wno-lint -Wno-style --top-module tb_idx_slice_reg_equiv -Mdir $W/obj $S > $W/build.log 2>&1 || { tail -20 $W/build.log; echo IDXB_BENCH_ERROR build; exit 2; }
X=$W/obj/Vtb_idx_slice_reg_equiv
if [ $M = pos ]; then $X > $W/run.log 2>&1; tail -3 $W/run.log; grep -q '^IDXSLICE_EQUIV_PASS' $W/run.log && { echo IDXB_PASS; exit 0; }; echo IDXB_BENCH_ERROR positive; exit 2
else $X +MUT > $W/run.log 2>&1; tail -3 $W/run.log; grep -q 'IDXSLICE_EQUIV_MISMATCH' $W/run.log && { echo IDXB_NEG_FAIL; exit 1; }; echo IDXB_BENCH_ERROR "mutant escaped"; exit 2; fi
