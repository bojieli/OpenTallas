#!/bin/bash
set -eu
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
cd /work/landing_keep
for kind in off on;do
 flag=;[ "$kind" != on ] || flag=-DOT_S81_RCK_RELAY4
 yosys -p "read_verilog -sv -DSYNTHESIS $flag /src/rtl/common/landed_parent/ot_pl_land.sv top.sv; hierarchy -top top; synth -flatten -noabc; opt_merge; write_json $kind.json" > "$kind.log" 2>&1
done
python3 - <<'PY'
import json
for kind in ['off','on']:
 d=json.load(open(kind+'.json'))['modules']['top'];n=d['netnames'];groups={}
 for field,owners in [('rq',['wa','wb','ra','rb']),('wc',['wa','wb']),('rc',['ra','rb']),('warm',['ra','rb'])]:
  values=[tuple(n[p+'.'+field]['bits']) for p in owners];groups[field]=len(set(values))
  if kind=='on':assert len(set(values))==len(values),(field,values)
 print(kind,groups)
print('PER_LANDING_CONTROL_COPIES_PRESERVED zero_RTL_cycle_change')
PY
