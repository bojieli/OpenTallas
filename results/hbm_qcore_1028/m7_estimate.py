"""Estimate only: original placement demand with permitted <=M7 layers.

No kit/plan ceiling is changed and no P&R/STA runs.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/hbm-cores-kits-5/aptools')
from geom_rules import Design,demand_metrics
root=Path('/srv/opentallas-scratch2/claude/codex-qcore-1028')
d=Design('/srv/opentallas-scratch2/claude/hbm-cores-kits-5/geom/ot_hbm_su_static_qcore_r13/geom.tsv')
out={'status':'ESTIMATE_ONLY_NO_CEILING_CHANGE','original_M5':{'h':1.275,'v':.811,'GRT50_overflow':1141},
 'M7_estimate':demand_metrics(d,max_layer='M7'),
 'assumptions':'Actual original placed nets and macro OBS; M6/M7 available to core in hypothetical ceiling. No die-over-core capacity reserved here.',
 'gate':'Requires die-owner/COORD plan ruling before any changed-ceiling build.'}
(root/'m7_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
