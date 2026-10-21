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

# Private TAP helper namespace avoids collision with existing red/sc bounded math.
sed -i "s/qfd_bmath_/qfd_s8tap_bmath_/g" "$out/qfd_dv_s8_tap_bounded.sv" "$out/qfd_dv_s8_tap_bounded_helpers.sv"
# Measured parent hw alias weights: retain existing edge/no-reset producer copies.
python3 tools/qwen_dv/s8_tap_alias_copies.py "$out/qfd_dv_s8_tap_bounded.sv" --record "$out/hw_alias_copies.json"
