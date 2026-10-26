#!/bin/bash
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
D=/srv/opentallas-scratch2/claude/codex-qc-token-current-0719
T=$D/source
P=$(readlink -f "$1")
TAG=$2
case "$TAG" in *[!a-zA-Z0-9_-]*|'') echo 'bad output tag'; exit 2;; esac
O=$D/plan_$TAG
[ ! -e "$O" ] || { echo "refuse existing output $O"; exit 2; }
mkdir "$O"
python3 - "$D" "$P" "$O" <<'PY'
from pathlib import Path
import json,sys,hashlib,shutil
D,P,O=map(Path,sys.argv[1:]);plan=json.loads(P.read_text())
assert plan.get('reset',{}).get('start')=='broadcast','current QC plan must declare START broadcast'
assert plan['die']['name']=='qwen_compute'
(O/'plan_sha256').write_text(hashlib.sha256(P.read_bytes()).hexdigest()+'\n')
(O/'plan_path').write_text(str(P)+'\n')
r=json.loads((D/'recipe.json').read_text());r.pop('land_align',None);r.pop('land_r8_extra',None);r.pop('param_regen',None)
(O/'probe_recipe.json').write_text(json.dumps(r,indent=1)+'\n')
for d in ['probe','base_r8','final']:
    q=O/d;q.mkdir()
    for n in ['asbuilt.json','asbuilt_sources.json']:shutil.copyfile(D/'elab_current'/n,q/n)
PY
bind_ok() {
    python3 - "$1/bind_report.json" <<'CHECK'
import json,sys
r=json.load(open(sys.argv[1]));assert r['n_errors']==0, r['errors']
for k in ['unbound','tied','undriven','multiply_bound']:assert r['proof'].get(k,0)==0,(k,r['proof'])
print('BIND_REPORT_PASS',sys.argv[1])
CHECK
}
cd "$T"
python3 tools/die_plan/bind.py bind "$P" --asbuilt "$O/probe_recipe.json" --out "$O/probe" > "$O/probe_bind.log" 2>&1
bind_ok "$O/probe"
python3 tools/die_plan/gen.py latency "$P" --groups "$O/probe/bus_groups.json" --out "$O/r8" > "$O/r8.log" 2>&1
python3 - "$O" <<'PY'
import json,sys
from pathlib import Path
O=Path(sys.argv[1]);r=json.loads((O/'probe_recipe.json').read_text());r['land_align']='r8';original=json.loads((O.parent/'recipe.json').read_text());r['param_regen']=original['param_regen'];r['land_r8']=str(O/'r8/qwen_compute_r8_landing.json');(O/'base_recipe.json').write_text(json.dumps(r,indent=1)+'\n')
PY
python3 tools/die_plan/bind.py bind "$P" --asbuilt "$O/base_recipe.json" --out "$O/base_r8" > "$O/base_bind.log" 2>&1
bind_ok "$O/base_r8"
python3 physical/die_plan/qwen_compute/bind/cb16_pads.py "$O/base_r8" "$O/r8/qwen_compute_r8_landing.json" "$O/cb16_pads.json" > "$O/cb16.log" 2>&1
python3 - "$O" <<'PY'
import json,sys
from pathlib import Path
O=Path(sys.argv[1]);r=json.loads((O/'base_recipe.json').read_text());r['land_r8_extra']=[str(O/'cb16_pads.json')];(O/'final_recipe.json').write_text(json.dumps(r,indent=1)+'\n')
PY
python3 tools/die_plan/bind.py bind "$P" --asbuilt "$O/final_recipe.json" --out "$O/final" > "$O/final_bind.log" 2>&1
bind_ok "$O/final"
python3 tools/die_plan/bind.py verify "$P" --asbuilt "$O/final_recipe.json" --out "$O/final" --mem 96 > "$O/verify.log" 2>&1
python3 tools/die_plan/regen_constants.py --die qwen_compute --bound "$O/final" --src-root "$T" --out-json "$O/constants.json" > "$O/constants.log" 2>&1
printf 'CURRENT_PLAN_BIND_PASS %s\n' "$O"
