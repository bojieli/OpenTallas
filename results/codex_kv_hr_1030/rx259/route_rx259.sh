#!/bin/bash
set -euo pipefail
K=/srv/opentallas-scratch2/claude/codex-kv-hr-1030/rx259
# Continue the already-validated same-source 3_place checkpoint; no synth/RTL change.
python3 - "$K" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1]);old=Path('/srv/opentallas-scratch2/claude/codex-kv-kits-2249/rx/kit259sw')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
items=[]
for f in sorted((p/'rtl').iterdir()):
 if f.is_file():
  assert sha(f)==sha(old/'rtl'/f.name),f.name
  items.append({'file':'rtl/'+f.name,'sha256':sha(f)})
n=next((p/'run/results').glob('asap7/*/base/1_2_yosys.v'));o=next((old/'run/results').glob('asap7/*/base/1_2_yosys.v'))
assert sha(n)==sha(o)
d=json.load(open(old/'lec/lec.json'));assert d['verdict']=='EQUIVALENT'
json.dump({'schema':'opentallas.same_source_proof_reuse.v1','prior_kit':str(old),'rtl_files':items,'netlist_sha256':sha(n),'prior_proof_sha256':sha(old/'lec/lec.json'),'verdict':'same-source pre-route EQ reused; actual post-route EQ still required','cycles_added':0},open(p/'pre_route_reuse.json','w'),indent=1)
PY
docker run --rm --name codex-kvhr1030-rx259-route --cpus 8 --memory 32g --memory-swap 32g -v "$K":/work -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M="make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES=8"; rc=0; $M cts > /work/route_continue.log 2>&1 && OT_VCLK_CORNER=ff $M grt HOLD_SLACK_MARGIN=10 >> /work/route_continue.log 2>&1 && $M route >> /work/route_continue.log 2>&1 && $M do-finish >> /work/route_continue.log 2>&1 || rc=$?; chown -R 1000:1000 /work; exit $rc'
bash "$K/run_kit_kv.sh" "$K" post 32 8
