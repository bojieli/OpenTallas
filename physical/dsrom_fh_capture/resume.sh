#!/bin/bash
# Resume a terminal floorplan recipe failure from the SAME mapped source.
# Invoke through unchanged admit.sh 48 after a fresh load<128 measurement.
set -euo pipefail
if [ "$#" -ne 1 ]; then echo 'Usage: resume.sh RUN_ROOT' >&2; exit 2; fi
S=$(realpath "$(dirname "$0")/../..")
R=$(realpath "$1")
cd "$S"
python3 - "$R" <<'PY'
import hashlib,json,os,sys
from pathlib import Path
p=json.loads(Path('SOURCE_PIN.json').read_text())
for f,h in p['sha256'].items():assert hashlib.sha256(Path(f).read_bytes()).hexdigest()==h,f
assert float(Path('/proc/loadavg').read_text().split()[0])<128
R=Path(sys.argv[1]);manifest=json.loads((R/'reuse.json').read_text())
for f,h in manifest['reused_sha256'].items():assert hashlib.sha256((R/'work/orfs'/f).read_bytes()).hexdigest()==h,f
cfg=R/'work/orfs/config.mk';text=cfg.read_text()
# Geometry is unchanged. Explicit DIE_AREA/CORE_AREA is mutually exclusive
# with CORE_UTILIZATION; remove only the conflicting initialization method.
assert 'export DIE_AREA = 0 0 2000 660' in text
assert 'export CORE_AREA = 2 2 1998 658' in text
text='\n'.join(l for l in text.splitlines() if not l.startswith(('export CORE_UTILIZATION =','export CORE_ASPECT_RATIO =','export CORE_MARGIN =')))+'\n'
text=text.replace('export POST_MACRO_PLACE_TCL =','export MACRO_PLACEMENT_TCL =')
if os.environ.get('OT_FH_PLACE_DENSITY'):
    density=float(os.environ['OT_FH_PLACE_DENSITY'])
    assert density==p['physical_parameters']['place_density'], 'Must match source-pinned measured region budget'
    assert 0<density<1
    text='\n'.join(l for l in text.splitlines() if not l.startswith(('export PLACE_DENSITY =','export PLACE_DENSITY_LB_ADDON =')))+'\n'
    text+=f'export PLACE_DENSITY = {density}\n'
assert os.environ.get('OT_FH_SHARED_PARTITION', 'none') == p['physical_parameters'].get('shared_partition', 'none')
assert (os.environ.get('OT_FH_VERTICAL_SEAMS') == '1') == p['physical_parameters'].get('vertical_seams', False)
assert (os.environ.get('OT_FH_DIAMOND_LEGALIZER') == '1') == p['physical_parameters'].get('diamond_legalizer', False)
if os.environ.get('OT_FH_DIAMOND_LEGALIZER') == '1':
    # C17 negotiation recovery leaves edge/padding violations; optional
    # DPO then introduces site-alignment/overlap errors. Use the installed
    # diamond legalizer and keep every original placement check/padding.
    text='\n'.join(l for l in text.splitlines() if not l.startswith(('export ENABLE_DPO =','export DETAIL_PLACEMENT_ARGS =')))+'\n'
    text+='export ENABLE_DPO = 0\nexport DETAIL_PLACEMENT_ARGS = -use_diamond_legalizer\n'
cfg.write_text(text)
print('SOURCE_PIN/reused objects verified',p['commit'],flush=True)
PY
uptime
free -g
df -h "$S" "$R"
B=$(python3 - "$R" <<'PY'
import re,sys
from pathlib import Path
root=Path(sys.argv[1])/'work/orfs'
name=re.search(r'^export DESIGN_NICKNAME = (\S+)$',(root/'config.mk').read_text(),re.M).group(1)
assert re.fullmatch(r'[A-Za-z0-9_]+',name)
print('/work/results/asap7/'+name+'/base')
PY
)
if [ "${OT_FH_ASSIGN_CONES:-0}" = 1 ]; then
 docker run --rm -e OMP_NUM_THREADS=16 \
  -e FHCONE_INPUT="$B/2_4_floorplan_pdn.odb" \
  -e FHCONE_OUTPUT="$B/2_4_floorplan_pdn.cones.odb" \
  -e FHCONE_RECEIPT=/work/cone_grouping.json \
  -e FHCONE_RECT_STRIPS="${OT_FH_RECT_STRIPS:-0}" \
  -e FHCONE_SHARED_PARTITION="${OT_FH_SHARED_PARTITION:-none}" \
  -e FHCONE_VERTICAL_SEAMS="${OT_FH_VERTICAL_SEAMS:-0}" \
  -v "$S:/src:ro" -v "$R/work/orfs:/work" openroad/orfs:latest bash -lc \
  'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -python /src/physical/dsrom_fh_capture/assign_lane_cones.py'
 # The original mapped floorplan is retained by the previous terminal run;
 # this continuation changes group metadata only, with its own hash receipt.
 python3 - "$R" <<'PY'
import json,os,shutil,sys
from pathlib import Path
r=Path(sys.argv[1])/'work/orfs'
p=json.loads((r/'cone_grouping.json').read_text())
assert not p['logic_changed'] and not p['macro_geometry_changed'] and not p['macro_pins_changed']
base=next(r.glob('results/asap7/*/base/2_4_floorplan_pdn.cones.odb')).parent
os.replace(base/'2_4_floorplan_pdn.cones.odb',base/'2_4_floorplan_pdn.odb')
# ORFS materializes its 2_floorplan alias as a regular file in this image.
shutil.copy2(base/'2_4_floorplan_pdn.odb',base/'2_floorplan.odb')
PY
fi
# Completed floorplan outputs are reusable only when explicitly hashed in
# reuse.json, just like the mapped synthesis outputs. Never replay synthesis.
REUSE_ARGS=$(python3 - "$R" <<'PY'
import json,sys
from pathlib import Path
m=json.loads((Path(sys.argv[1])/'reuse.json').read_text())
for f in m['reused_sha256']:
    if Path(f).name in {x+'.'+ext for x in ('1_synth','2_1_floorplan','2_2_floorplan_macro','2_3_floorplan_tapcell','2_4_floorplan_pdn','2_floorplan') for ext in ('odb','sdc')}:
        print('-o /work/'+f,end=' ')
PY
)
exec docker run --rm -e OMP_NUM_THREADS=16 -v "$S:/src:ro" -v "$R/work/orfs:/work" \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc \
 "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 $REUSE_ARGS finish metadata-generate"
