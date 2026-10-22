#!/usr/bin/env bash
set -euo pipefail
out=$1
mkdir -p "$out"
python3 - "$out" <<'GEN'
from pathlib import Path
import sys,re
text=Path('rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv').read_text()
text=text.replace('module qfd_dv_s6_tap (','module qfd_dv_s8_tap_seed (',1)
# Actual E1 publications: six source copies, each <=12 D terminals, no extra stage.
text=text.replace('module qfd_dv_s6_xs_tap (','module qfd_dv_s8_xs_tap_seed (',1).replace('qfd_dv_s6_xs_tap u_tap','qfd_dv_s8_xs_tap_seed u_tap')
text=text.replace('    input  wire           xt_v,','    input wire [5:0] xt_vcopies,\n    input  wire           xt_v,',1)
text=text.replace('    input  wire              sw_v,','    input wire [5:0] sw_vcopies,\n    input  wire              sw_v,',1)
assert 'sw_vcopies' in text
text=text.replace('.sw_v(xt_v),','.sw_vcopies(xt_vcopies), .sw_v(xt_v),',1)
text=text.replace('.d(sw_v), .q(s1_vl[gl])','.d(sw_vcopies[gl/12]), .q(s1_vl[gl])')
text=text.replace('.d(sw_v), .q(s1_vc)','.d(sw_vcopies[5]), .q(s1_vc)').replace('.d(sw_v), .q(s1_vf)','.d(sw_vcopies[5]), .q(s1_vf)')
assert text.count('.d(sw_vcopies[')==3
Path(sys.argv[1]+'/tap_seed.sv').write_text(text)
GEN
yosys -p "read_verilog -sv -DSYNTHESIS $out/tap_seed.sv; hierarchy -check -top qfd_dv_s8_tap_seed; synth -top qfd_dv_s8_tap_seed -flatten -noabc -nofsm -noshare; dffunmap; write_json $out/tap.json" > "$out/yosys.log" 2>&1
python3 tools/qwen_dv/ctlm6_bound_macro.py "$out/tap.json" --top qfd_dv_s8_tap_seed --name qfd_dv_s8_tap_bounded --out "$out/qfd_dv_s8_tap_bounded.sv" --helpers "$out/qfd_dv_s8_tap_bounded_helpers.sv" --record "$out/source_record.json" --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb
# QE3-SLICE2 10-21: private helper namespace. The shared qfd_bmath_* helpers are byte-identical to the subset in
# rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4_helpers.sv, which the same s8 parent also reads -> Yosys -defer refused the
# re-definition (w12c/w12cb census). Rename only; cells, IDs and keep_hierarchy are unchanged.
sed -i 's/\bqfd_bmath_/qfd_s8tap_bmath_/g' "$out/qfd_dv_s8_tap_bounded.sv" "$out/qfd_dv_s8_tap_bounded_helpers.sv"
# QE3-SLICE2B 10-21: kept same-edge copies of the flops replicated into >3 hw bits (census u_114..u_118 48/96 loads).
python3 tools/qwen_dv/s8_tap_hw_copies.py "$out/qfd_dv_s8_tap_bounded.sv" 3
