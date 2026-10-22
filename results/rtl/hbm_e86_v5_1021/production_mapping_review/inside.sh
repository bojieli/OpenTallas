#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
python3 - <<'VERIFY'
import json,hashlib,pathlib
rows=json.load(open('/work/image_libs.json'))
for r in rows:
 p=pathlib.Path(r['path']); assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],str(p)
print('ALL8_IMAGE_RVT_TT_LIBERTY_HASHES_MATCH')
VERIFY
python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts
python3 /src/tools/orfs_allcorner_spef.py /OpenROAD-flow-scripts/flow/scripts/final_outputs.tcl
G=/work/results/asap7/opentallas_e86v5_production_mapping/base/1_2_yosys.v
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 -n "$G" > /work/effective_make_dryrun.log
make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=8 "$G" 2>&1 | tee /work/orfs_synth.log
cp "$G" /work/1_2_yosys.raw.v
python3 - <<'CENSUS'
import json,subprocess,sys
libs=json.load(open('/work/image_libs.json'))
args=[sys.executable,'/src/tools/ref_tile/native_census.py','--netlist','/work/1_2_yosys.raw.v','--top','ot_hgi_coll_tkm_tile_e86_v5','--out','/work/native_census.json']
for x in libs: args.extend(['--liberty',x['path']])
raise SystemExit(subprocess.call(args))
CENSUS
