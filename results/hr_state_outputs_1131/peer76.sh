#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/peer76"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
python3 - <<'PY'
import json,importlib.util,pathlib
s=importlib.util.spec_from_file_location('H','../hr_state_outputs.py');H=importlib.util.module_from_spec(s);s.loader.exec_module(H)
old=json.load(open('cone_manifest.json'))
source=json.load(open('flat.json'));out,manifest=H.stage(source,'qkd_hr_core_peer',list(old))
assert len(manifest['outputs'])==76
json.dump(out,open('cone_stage_generic.json','w'));json.dump(manifest,open('generic_manifest.json','w'))
# Adapter retains the parent's exact native-cut vehicle; only generated naming changes.
p=pathlib.Path('coupon.py').read_text().replace("cn.startswith('peer_retime_next_') or cn.startswith('peer_comb_ff_')","cn.startswith('hrs_next_') or cn.startswith('hrs_private_')")
pathlib.Path('coupon_generic.py').write_text(p)
PY
yosys -Q -T -p 'read_json cone_stage_generic.json; opt_expr; opt_clean; write_json folded_generic.json' > fold_generic.log 2>&1
python3 ../hr_state_outputs.py finish folded_generic.json retimed.json generic_manifest.json > finish_generic.log
python3 coupon_generic.py > cut_generic.log
cp coupon.ys generic.ys
yosys -Q -T generic.ys > generic.log 2>&1
python3 - <<'PY'
import json
j=json.load(open('coupon_gate_clean.json'));m=j['modules']['gate'];n=max(b for c in m['cells'].values() for bs in c['connections'].values() for b in bs if isinstance(b,int))+1
c=next(c for name,c in m['cells'].items() if name.startswith('hrs_private_'));old=c['connections']['D'][0];c['connections']['D']=[n]
m['cells']['hrs_coupon_mutant']=dict(hide_name=0,type='$not',parameters=dict(A_SIGNED='0',A_WIDTH=format(1,'032b'),Y_WIDTH=format(1,'032b')),attributes={},port_directions=dict(A='input',Y='output'),connections=dict(A=[old],Y=[n]))
json.dump(j,open('coupon_mut.json','w'))
PY
sed 's/read_json coupon_gate_clean.json/read_json coupon_mut.json/' generic.ys | sed '/read_json coupon_gate.json/,/write_json coupon_gate_clean.json/d' > generic_mut.ys
# Use the already-normalized native and mutant coupon modules directly.
cat > generic_mut.ys <<'YS'
read_json coupon_gold_clean.json
read_json coupon_mut.json
equiv_make gold gate eq
hierarchy -top eq
async2sync
equiv_simple -seq 2
equiv_induct -seq 2
equiv_status -assert
YS
set +e;yosys -Q -T generic_mut.ys > generic_mut.log 2>&1;rc=$?;set -e
echo "$rc" > rc_mutant
test "$rc" = 1
printf 'GENERIC_PEER_NATIVE76 PASS/MUT1\n'
