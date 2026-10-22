#!/bin/bash
set -euo pipefail
mkdir -p out
python3 - <<'PY2'
import json,glob
from pathlib import Path
s=json.load(open('sources.json'));libs=sorted(glob.glob('libs/*.lib'));p='\n'.join('read_liberty -lib '+l for l in libs);a=' '.join('-liberty '+l for l in libs)
ys='read_verilog -sv -DSYNTHESIS -DOT_FP_DATA_NORST '+' '.join(s['sources'])+'\nblackbox ot_hbm_hc_tail_child_static\nchparam '+' '.join('-set '+k+' '+str(v) for k,v in s['params'].items())+' ot_hbm_hc_root_static\nhierarchy -check -top ot_hbm_hc_root_static\ntcl physical/common_flow/ot_keep_regs.tcl\nsynth -top ot_hbm_hc_root_static -noshare\ndfflibmap -liberty '+next(l for l in libs if '_SEQ_' in l)+'\nabc '+a+'\nopt_clean -purge\n'+p+'\nsetattr -mod -unset keep_hierarchy\nflatten\nopt_clean -purge\nhierarchy -check -top ot_hbm_hc_root_static\nwrite_json out/mapped.json\nwrite_verilog -noattr out/mapped.v\ntee -o out/stat.txt stat\n'
Path('out/parent.ys').write_text(ys)
PY2
yosys -q -l out/synth.log out/parent.ys
args=();for f in libs/*.lib physical/asap7_memory_macros_v2/*/*_tt.lib results/rtl/hbm_hc_root_safe_1020/root_fs/tail_child_stub_tt.lib;do args+=(--liberty "$f");done
python3 tools/ref_tile/native_census.py --netlist out/mapped.v --top ot_hbm_hc_root_static --out out/native.json "${args[@]}" > out/native.log 2>&1
echo $? > out/native.rc
