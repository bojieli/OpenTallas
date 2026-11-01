#!/bin/bash
set -euo pipefail
D=/srv/opentallas-scratch2/claude/codex-head-pins-1131
K=$D/mesh_combined/gen/hd_mesh_e
docker run --rm --name codex-head-mesh-combined-1131 --memory=8g --memory-swap=8g --cpus=4 -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; set -e; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=4 do-5_1_grt; openroad -exit /work/combined_post.tcl > /work/combined_post.log 2>&1' > "$D/mesh_combined/grt.log" 2>&1
python3 - "$K" <<'PY'
import csv,json,sys
from pathlib import Path
K=Path(sys.argv[1]);rows=list(csv.DictReader((K/'combined_clock_census.tsv').open(),delimiter='\t'))
clocks={r['net']for r in rows if r['class']=='CLOCK' and int(r['degree'])>1}
guides=list((K/'run/results').rglob('*.guide'));assert guides,'native route.guide absent'
names=set()
for p in guides:
    previous=''
    for line in p.open():
        s=line.strip()
        if s=='(':names.add(previous.lstrip('\\'))
        if s:previous=s
missing=sorted(clocks-names)
cts={}
for p in (K/'run/logs').rglob('4_1_cts.json'):
    d=json.loads(p.read_text());cts[str(p)]={k:v for k,v in d.items()if 'clock' in k.lower() or 'cts' in k.lower()}
result=dict(method='normal ORFS combined GRT, original special flags untouched',clock_connected=len(clocks),clock_missing_native_guide=missing,native_guides=[str(p)for p in guides],cts_actual_metrics=cts,net_census='combined_clock_census.tsv',clock_pin_coverage='clock_pin_coverage.tsv',actual_clock_roots='clock_roots.tsv',qualified_clock_occupancy=bool(clocks)and not missing)
(K/'combined_coverage.json').write_text(json.dumps(result,indent=1)+'\n')
assert result['qualified_clock_occupancy'],missing
assert cts,'actual CTS metrics missing'
PY
mkdir -p "$D/mesh_combined/geom"
python3 - "$D" <<'PY'
import json,sys
from pathlib import Path
D=Path(sys.argv[1]);K=D/'mesh_combined/gen/hd_mesh_e';O=D/'mesh_combined/geom'
(O/'check.json').write_text(json.dumps(dict(id='head-mesh-combined-1131',odb=str(K/'run/results/asap7/dp_hd_mesh_e/base/5_1_grt.odb'),image='openroad/orfs:asap7lock',mem_gb=4,grt=False,rules_args=['--all-kits','--outline','838.08x86.4','--grt-log',str(D/'mesh_combined/grt.log'),'--title','HEAD mesh actual combined CLOCK+SIGNAL GRT']),indent=1)+'\n')
PY
bash "$D/src/tools/autopilot/geom_check.sh" "$D/mesh_combined/geom" > "$D/mesh_combined/geom.log" 2>&1
echo 'PROBE COMPLETE ONLY: review CTS arrivals/hold, reach<=405 and actual clock census before DRT'
