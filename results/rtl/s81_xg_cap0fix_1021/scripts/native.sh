#!/usr/bin/env bash
set -euo pipefail
R=$(pwd)
export OT_ORFS_CORNER_OVERRIDE=TC
export OT_ROUTE_HOLD_CORNERS=mm
export OT_MM_FF_SDC=physical/ref_tile/s81sl_xgtxo_b/signoff.sdc
# Original failing gate config + exact immutable snapshot, changed xs4 source only.
docker run --rm -v "$R/src:/src:ro" -v "$R/native:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base synth' > native/synth.log 2>&1
python3 - <<'P'
import json,subprocess,os
r=os.getcwd(); b=json.load(open('baseline_native.json'))
c=['docker','run','--rm','-v',r+'/src:/src:ro','-v',r+'/native:/work','openroad/orfs:latest','python3','/src/tools/ref_tile/native_census.py','--netlist',b['netlist']['path'],'--top',b['top'],'--kit','s81sl_xgtxo_b','--out','/work/native_census.json']
for x in b['liberty']: c+=['--liberty',x['path']]
subprocess.run(c,check=True)
s=json.load(open('native/native_census.json'));print('NATIVE',s['status'],s['max_dynamic_loads'],len(s['violations']),len(s['role_errors']))
P
