#!/bin/bash
# QC-TYPES-9/REACH: strict native bind of plan_qc53v4w with the R8 table re-derived on its bus_groups (only the 36 cw_n
# members change: bound/landed +3, pad 0)
set -u
Q=/srv/opentallas-scratch2/claude/qct9; W=$Q/reach; F=$Q/farm; cd $F
P=physical/die_plan/qwen_compute/plan_of_record/plan_qc53v4w.json
RT=physical/die_plan/qwen_compute/qc_start_1106/runtime
cp $W/r8/qwen_compute_r8_landing.json $RT/r8_reach.json
python3 -B - $W/asbuilt_reach.json $RT/asbuilt_reach.json <<'PY'
import json,sys
a=json.load(open(sys.argv[1])); a['land_r8']='physical/die_plan/qwen_compute/qc_start_1106/runtime/r8_reach.json'
a['land_r8_note']=a.get('land_r8_note','')+' | QC-TYPES-9/REACH 11-08: r8_reach.json = r8.py pads (defaults) on the plan_qc53v4w bind bus_groups; vs r8.json only the 36 cw_n members change (bound/landed +3, pad 0)'
open(sys.argv[2],'w').write(json.dumps(a,indent=1)+'\n'); open(sys.argv[1],'w').write(json.dumps(a,indent=1)+'\n')
PY
date
python3 -B tools/die_plan/bind.py bind $P --out $W/bind_v4w --strict --asbuilt $RT/asbuilt_reach.json > $W/bind2.log 2>&1; echo "BIND rc $?" >> $W/bind2.log
date
