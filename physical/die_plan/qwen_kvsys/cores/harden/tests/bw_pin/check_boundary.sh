#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
for pair in 'ref:qkd_kv_es_fan_root2_b_nc32' 'new:qkd_kv_es_fan_root2_b_nc32_bpin'; do
  file=${pair%%:*}; top=${pair#*:}
  yosys -Q -T -p "read_verilog -sv -noautowire -DSYNTHESIS $file.sv; hierarchy -top $top -chparam S32 1 -chparam PH1C 1; proc; flatten; opt_clean; write_json $file.json" > "$file.synth.log" 2>&1
done
python3 - <<'PY'
import json
out={}
for f in ['ref','new']:
 d=json.load(open(f+'.json'));m=next(iter(d['modules'].values()));bit=m['ports']['bw']['bits'][0];loads=[]
 for name,c in m['cells'].items():
  for p,b in c['connections'].items():
   if c['port_directions'][p]=='input' and bit in b:loads.append((name,c['type'],p))
 out[f]=loads
assert any(not t.startswith(('$dff','$adff','$sdff')) for n,t,p in out['ref']),out
assert len(out['new'])==1 and out['new'][0][1].startswith(('$dff','$adff','$sdff')) and out['new'][0][2]=='D',out
open('boundary.json','w').write(json.dumps(out,indent=1)+'\n')
print('BW_PIN_BOUNDARY PASS raw_valid combinational_loads_removed sole_capture_D')
PY
