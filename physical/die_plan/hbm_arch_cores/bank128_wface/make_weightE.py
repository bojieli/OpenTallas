from pathlib import Path
import json,hashlib
r=Path('/srv/opentallas-scratch2/claude/codex-bank128-wface');c=r/'context_weightE';base=json.loads((r/'context/base_freeze.json').read_text());f=c/'cores/ot_hbm_hc_bank128_pair_core__250.56x267.84__weight_E.json';h=hashlib.sha256(f.read_bytes()).hexdigest();base['view']=base['module']+'@'+h[:12];base['pins_file']='cores/'+f.name;base['pins_sha256']=h;(c/'base_freeze.json').write_text(json.dumps(base,indent=1)+'\n');p=c/'die_plan.json'
if p.is_symlink():p.unlink()
if not p.exists():p.hardlink_to(r/'context/die_plan.json')
print(base['view'])
