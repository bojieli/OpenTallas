#!/bin/bash
set -euo pipefail
base=$1
python3 - "$base" <<'PY'
from pathlib import Path
import sys,re,json
base=Path(sys.argv[1]);s=(base/'1_2_yosys.v').read_text();pat=r'(DFF\S+\s+\\u_ot_pr_core\.u_rly\.fan\[0\]\$_DFF_P_\s*\(.*?\.D\()(.*?)(\))';m=re.search(pat,s,re.S)
if not m:raise RuntimeError('mapped causal fan[0] D cell not located')
mut=s[:m.start(2)]+'~('+m[2]+')'+s[m.end(2):];Path('mapped_wrong.v').write_text(mut)
Path('out/mutation.json').write_text(json.dumps({'kind':'actual_mapped_fan0_D_inversion','original_D':m[2],'target':'u_ot_pr_core.u_rly.fan[0]$_DFF_P_','original_unchanged':True},indent=2))
libs=sorted(Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM').glob('*RVT_TT*.lib*'))
if len(libs)!=5:raise RuntimeError('expected exactly5 actual NLDM RVT TT libs')
for name,mp in [('positive',str(base/'1_2_yosys.v')),('negative','mapped_wrong.v')]:
 lines=['read_liberty -ignore_miss_func '+str(p) for p in libs]
 lines+=['read_verilog -sv '+mp,'hierarchy -top qkd_kvs_hroot_safe32','proc','flatten','opt_clean','rename qkd_kvs_hroot_safe32 gate_top','design -stash mapped','read_verilog -sv core.sv gold_inner.sv '+str(base/'ot_rst_land_wrapper.v'),'hierarchy -top qkd_kvs_hroot_safe32','proc','flatten','opt_clean','rename qkd_kvs_hroot_safe32 gold_top','design -stash source','design -copy-from mapped -as gate_top gate_top','design -copy-from source -as gold_top gold_top','read_verilog -sv miter.sv','hierarchy -top leaf_equiv','proc','flatten','opt_clean','async2sync','dffunmap','opt_clean','write_json out/'+name+'_miter.json','stat','sat -seq 16 -prove ok 1 -verify -set-at 1 rst_n 0 -set-at 2 rst_n 0 -set-at 3 rst_n 0 -set-at 4 rst_n 0 -set-at 5 rst_n 0 -set-at 6 rst_n 0 '+ ' '.join('-set-at '+str(k)+' rst_n 1' for k in range(7,17))+' -show-inputs -dump_json out/'+name+'_counterexample.json']
 Path(name+'.ys').write_text('\n'.join(lines)+'\n')
PY
yosys -Q -s positive.ys > out/positive.log 2>&1
set +e
yosys -Q -s negative.ys > out/negative.log 2>&1
rc=$?
set -e
printf 'negative_rc=%s\n' "$rc" > out/status.txt
[ "$rc" != 0 ] && grep -q 'proof did fail' out/negative.log
