#!/bin/bash
set -euo pipefail
python3 tools/hbm_hc/bound_fanout_clone.py out/mapped.json --top ot_hbm_hc_root_static --name ot_hbm_hc_root_static_bfc --out out/native_bfc.v --limit 24 > out/clone.log 2>&1
python3 - <<'PYS'
from pathlib import Path
import glob
ls=sorted(glob.glob('libs/*.lib'));a=' '.join('-liberty '+p for p in ls)
ys='\n'.join('read_liberty -lib '+p for p in ls)+'\nread_verilog -sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v\nread_verilog -sv -DSYNTHESIS rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_tail_child_static.sv\nblackbox ot_hbm_hc_tail_child_static\nread_verilog out/native_bfc.v\nhierarchy -check -top ot_hbm_hc_root_static_bfc\ntcl physical/common_flow/ot_keep_regs.tcl\nsynth -top ot_hbm_hc_root_static_bfc -flatten -noshare\nabc '+a+'\nopt_clean\nwrite_verilog -noattr out/retained.v\ntee -o out/stat_retained.txt stat\n'
Path('out/retain.ys').write_text(ys)
PYS
yosys -q -l out/retain.log out/retain.ys
args=();for f in libs/*.lib physical/asap7_memory_macros_v2/*/*_tt.lib results/rtl/hbm_hc_root_safe_1020/root_fs/tail_child_stub_tt.lib;do args+=(--liberty "$f");done
set +e
python3 tools/ref_tile/native_census.py --netlist out/retained.v --top ot_hbm_hc_root_static_bfc --out out/native_retained.json "${args[@]}" > out/native_retained.log 2>&1
rc=$?;echo "$rc" > out/native_retained.rc
exit "$rc"
