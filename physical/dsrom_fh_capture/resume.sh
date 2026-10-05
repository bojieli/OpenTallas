#!/bin/bash
# Resume a terminal floorplan recipe failure from the SAME mapped source.
# Invoke through unchanged admit.sh 48 after a fresh load<128 measurement.
set -euo pipefail
if [ "$#" -ne 1 ]; then echo 'Usage: resume.sh RUN_ROOT' >&2; exit 2; fi
S=$(realpath "$(dirname "$0")/../..")
R=$(realpath "$1")
cd "$S"
python3 - "$R" <<'PY'
import hashlib,json,sys
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
# Completed floorplan outputs are reusable only when explicitly hashed in
# reuse.json, just like the mapped synthesis outputs. Never replay synthesis.
REUSE_ARGS=$(python3 - "$R" <<'PY'
import json,sys
from pathlib import Path
m=json.loads((Path(sys.argv[1])/'reuse.json').read_text())
for f in m['reused_sha256']:
    if f.endswith(('/1_synth.odb','/1_synth.sdc','/2_1_floorplan.odb','/2_1_floorplan.sdc')):
        print('-o /work/'+f,end=' ')
PY
)
exec docker run --rm -e OMP_NUM_THREADS=16 -v "$S:/src:ro" -v "$R/work/orfs:/work" \
 -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc \
 "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 $REUSE_ARGS finish metadata-generate"
