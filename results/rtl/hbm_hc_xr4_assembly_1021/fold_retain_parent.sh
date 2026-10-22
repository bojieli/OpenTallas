#!/bin/bash
set -euo pipefail
mkdir -p out_fold
args=();for f in libs/*.lib;do args+=(--liberty "$f");done
python3 tools/hbm_hc/const_identity_fold.py out/mapped.json out_fold/mapped.json --top ot_hbm_hc_root_static "${args[@]}" > out_fold/fold.log 2>&1
python3 tools/hbm_hc/bound_fanout_clone.py out_fold/mapped.json --top ot_hbm_hc_root_static --name ot_hbm_hc_root_static_bfc --out out_fold/native_bfc.v --limit 24 > out_fold/clone.log 2>&1
python3 - <<'PYS'
from pathlib import Path
import glob
ls=sorted(glob.glob('libs/*.lib'));a=' '.join('-liberty '+p for p in ls)
ys='\n'.join('read_liberty -lib '+p for p in ls)+'\nread_verilog -sv physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v\nread_verilog -sv -DSYNTHESIS rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_tail_child_static.sv\nblackbox ot_hbm_hc_tail_child_static\nread_verilog out_fold/native_bfc.v\nhierarchy -check -top ot_hbm_hc_root_static_bfc\ntcl physical/common_flow/ot_keep_regs.tcl\nsynth -top ot_hbm_hc_root_static_bfc -flatten -noshare\nabc '+a+'\nopt_clean\nwrite_verilog -noattr out_fold/retained.v\ntee -o out_fold/stat_retained.txt stat\n'
Path('out_fold/retain.ys').write_text(ys)
PYS
yosys -q -l out_fold/retain.log out_fold/retain.ys
args=();for f in libs/*.lib physical/asap7_memory_macros_v2/*/*_tt.lib results/rtl/hbm_hc_root_safe_1020/root_fs/tail_child_stub_tt.lib;do args+=(--liberty "$f");done
set +e
python3 tools/ref_tile/native_census.py --netlist out_fold/retained.v --top ot_hbm_hc_root_static_bfc --out out_fold/native_retained.json "${args[@]}" > out_fold/native_retained.log 2>&1
rc=$?;echo "$rc" > out_fold/native_retained.rc
exit "$rc"
