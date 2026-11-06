#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
TASK_ROOT=$PWD
KIT="$TASK_ROOT/kits/ot_svgr_own_2054dcac0c09-headtail_p37"
DK=(docker)
docker ps >/dev/null 2>&1 || DK=(sudo docker)
"${DK[@]}" run --rm --name "svgr-head-synth-$USER-$$" --cpus=2 --memory=4g --memory-swap=4g -e HUID="$(id -u)" -e HGID="$(id -g)" -v "$KIT:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=2 synth; rc=$?; chown -R "$HUID:$HGID" /work/run; exit "$rc"' > "$TASK_ROOT/synth_stdout.log" 2>&1
python3 - "$TASK_ROOT" <<'PY'
import pathlib,json,sys,hashlib
p=pathlib.Path(sys.argv[1]);kit=p/'kits/ot_svgr_own_2054dcac0c09-headtail_p37'; f=json.loads((kit/'freeze.json').read_text());m=json.loads(next((kit/'run/logs/asap7').glob('*/base/1_synth.json')).read_text());n=m['synth__design__instance__count__stdcell'];area=m['synth__design__instance__area__stdcell'];w,h=f['outline_um'];free=(w-8.64)*(h-8.64);util=area/free
j=dict(verdict='PASS' if n<=150000 and util<=.45 else 'FAIL',kit_hash=f['kit_hash'],view=f['view'],outline_um=[w,h],standard_cells=n,standard_area_um2=area,nonmacro_core_area_um2=free,standard_utilization=util,limits=dict(cells=150000,standard_utilization=.45),mapped_only=True,placement_run=False,route_run=False,source_recipe='ot_svgr_own__headtail',source_commit='40139073ec3ce4fa4fca4f81d16ee5192d4f245c',backend_commit='27cdbd816b0c86654f2e94ed1ab9dde2d9a162dc')
(p/'mapped_size.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2));assert j['verdict']=='PASS'
PY
