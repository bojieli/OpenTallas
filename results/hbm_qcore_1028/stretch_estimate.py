"""One reach-safe lot-height counterfactual, estimate only; no plan edits."""
import sys,json
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/hbm-cores-kits-5/aptools')
from geom_rules import Design,demand_metrics,r2r_metrics
d=Design('/srv/opentallas-scratch2/claude/hbm-cores-kits-5/geom/ot_hbm_su_static_qcore_r13/geom.tsv')
old_h,new_h=207.36,311.04
scale=(new_h-8.64)/(old_h-8.64)
def sy(y):return 4.32+(y-4.32)*scale
for i,c in list(d.cells.items()):
 k,m,x0,y0,x1,y1,n=c;cy=sy((y0+y1)/2);hy=(y1-y0)/2
 d.cells[i]=(k,m,x0,cy-hy,x1,cy+hy,n)
for p in d.pins:
 p['y']=p['y'] if p['y']<1 else p['y']+new_h-old_h if p['y']>old_h-1 else sy(p['y'])
d.die=(0.,0.,224.64,new_h)
out={'status':'ESTIMATE_ONLY_NO_PLAN_CHANGE','outline_um':[224.64,new_h],
 'source_outline_um':[224.64,old_h],'height_area_delta_percent':50,
 'method':'Affine source placement/capture groups and pin/island locations in y; physical cell/macro sizes unchanged.',
 'demand':demand_metrics(d),'reach':r2r_metrics(d),
 'limits':'Does not establish placement legalization or CTS; interfaces/clock/reset entries move and require one die-owner plan event.'}
Path('/srv/opentallas-scratch2/claude/codex-qcore-1028/stretch_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
