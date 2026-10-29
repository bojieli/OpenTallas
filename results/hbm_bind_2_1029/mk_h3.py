# HBM-BIND-2 h3 = h1 + dead-input proof for u_qlate.rst_n applied to a plan COPY (validation only; plan owner DIE-HBM-14
# applies the same declarations in the C25c event via tools/die_plan/dead_inputs.apply_plan_declarations).
import json,sys,os,shutil
from pathlib import Path
R=Path('/srv/opentallas-scratch2/claude/hbm-bind-2-1029');W=Path('/srv/opentallas-scratch2/claude/wt/hbm-bind-2-1029')
C=Path('/srv/opentallas-scratch2/claude/codex-hbm-bind-0300/plan');P=R/'h3plan';P.mkdir(exist_ok=True)
for x in C.iterdir():
    if x.name!='die_plan.json' and not (P/x.name).exists(): os.symlink(x,P/x.name)
rel='results/hbm_bind_2_1029/dead_qlate_proof.json';(W/rel).parent.mkdir(parents=True,exist_ok=True)
shutil.copy(R/'dead_qlate/proof.json',W/rel)
sys.path.insert(0,str(W/'tools/die_plan'));import dead_inputs
p=json.loads((C/'die_plan.json').read_text());n=dead_inputs.apply_plan_declarations(p,rel,W)
(P/'die_plan.json').write_text(json.dumps(p))
D=R/'h3';(D/'out').mkdir(parents=True,exist_ok=True)
a=json.loads((R/'h1/asbuilt_b.json').read_text());a['dead_input_proofs']=[rel];a['note']='HBM-BIND-2 h3 (h1 + u_qlate dead-input proof) | '+a['note']
(D/'asbuilt_b.json').write_text(json.dumps(a,indent=1));print('declarations',n)
