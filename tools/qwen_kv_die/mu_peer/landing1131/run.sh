#!/bin/bash
set -euo pipefail
D=$(pwd)
cd "$D"
cat > pre.ys <<'YS'
read_verilog -defer -sv native.sv
hierarchy -top ot_qwen_tp8_token_cohort_mu
proc
flatten
memory_collect
opt_clean
write_json pre.json
YS
Y=/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys
DK=(docker run --rm -v "$D:$D" -w "$D" openroad/orfs:asap7lock)
"${DK[@]}" "$Y" -Q -T -l pre.log pre.ys
python3 landing_profile.py pre.json post.json ledger.json --top ot_qwen_tp8_token_cohort_mu --clock clk
python3 - <<'PY'
import json
j=json.load(open('post.json'));j['modules']['peer_profile']=j['modules'].pop('ot_qwen_tp8_token_cohort_mu');json.dump(j,open('gate.json','w'))
PY
printf 'read_json gate.json\nselect peer_profile\nwrite_verilog -selected gate.sv\n' > emit.ys
"${DK[@]}" "$Y" -Q -T -l emit.log emit.ys
iverilog -g2012 -s tb -o sim native.sv gate.sv tb.sv
vvp sim | tee base.log
python3 - <<'PY'
import json
j=json.load(open('gate.json'));m=j['modules']['peer_profile'];c=next(c for n,c in m['cells'].items() if n.startswith('peer_land_out_'));q=c['connections']['Q'][0];nid=max(b for c in m['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
m['cells']['mutation']={'type':'$not','parameters':{'A_SIGNED':'0'*32,'A_WIDTH':format(1,'032b'),'Y_WIDTH':format(1,'032b')},'attributes':{},'port_directions':{'A':'input','Y':'output'},'connections':{'A':c['connections']['D'],'Y':[nid]}};c['connections']['D']=[nid];json.dump(j,open('mut.json','w'))
PY
printf 'read_json mut.json\nselect peer_profile\nwrite_verilog -selected mutant.sv\n' > mut.ys
"${DK[@]}" "$Y" -Q -T -l mut.log mut.ys
iverilog -g2012 -s tb -o sim_mut native.sv mutant.sv tb.sv
set +e
vvp sim_mut > mutant.log 2>&1
rc=$?
set -e
cat mutant.log
[ "$rc" -ne 0 ]
printf 'base rc=0\nmutant rc=%s\n' "$rc" > receipt.txt
