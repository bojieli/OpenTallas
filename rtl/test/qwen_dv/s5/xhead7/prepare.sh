#!/bin/bash
# QW-SLICE7-LEAVES XHEAD: generic synthesis of qfd_dv_s5_xhead_rt (retag in front of the output registers) and the bounded
# constructor (same flags as CTL repair4), main (XH_MUT 0) + real functional mutant (XH_MUT 1: N retag taken as S).
# Run on the FLEET from the repository root: bash rtl/test/qwen_dv/s5/xhead7/prepare.sh OUT
set -euo pipefail
O=$1; mkdir -p "$O"
SRC="rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv rtl/qwen_dv/s5/qfd_dv_s5_xhead_rt.sv rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_pipe.sv"
FL="${XH_FLAGS:---load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb --fuse-ao}"
for m in 0 1; do
  n=qfd_dv_s5_xhead_bounded; [ $m = 1 ] && n=qfd_dv_s5_xhead_bounded_mut
  yosys -Q -p "read_verilog -sv $SRC; chparam -set XH_MUT $m qfd_dv_s5_xhead_rt; hierarchy -check -top qfd_dv_s5_xhead_rt; synth -top qfd_dv_s5_xhead_rt -flatten -noabc -nofsm -noshare; dffunmap; clean; stat; write_json $O/generic$m.json" > "$O/generic$m.log" 2>&1
  python3 tools/qwen_dv/bound_math_netlist.py "$O/generic$m.json" $FL --top qfd_dv_s5_xhead_rt --name $n \
    --out "$O/$n.sv" --helpers "$O/helpers$m.sv" --record "$O/model$m.json" > "$O/construct$m.log" 2>&1
done
cmp "$O/helpers0.sv" "$O/helpers1.sv" && echo "HELPERS IDENTICAL"
grep -iE 'cells|DFF' "$O/generic0.log" | tail -14 || true
echo PREPARE_DONE
