"""Convert a finite packed body-origin plan to canonical compiler cell centres."""
import json,sys
from pathlib import Path
source,out=sys.argv[1:];s=json.load(open(source));t=s['core_tree'];widths={'BUFx4_ASAP7_75t_R':.378,'BUFx6f_ASAP7_75t_R':.540,'BUFx8_ASAP7_75t_R':.648,'BUFx10_ASAP7_75t_R':.756,'BUFx12f_ASAP7_75t_R':.972,'BUFx16f_ASAP7_75t_R':1.188,'BUFx24_ASAP7_75t_R':1.620}
if t.get('coordinate_basis')=='cell_centres':raise ValueError('already canonical centres')
for n in t['nodes']:
 x,y=n['xy_um'];n['body_origin_um']=[x,y];n['xy_um']=[round(x+widths[n['master']]/2,6),round(y+.135,6)]
t['coordinate_basis']='cell_centres';t.pop('model_qualification',None)
for l in t['leaves']:l.pop('pin_latency_ps',None)
Path(out).write_text(json.dumps(s,indent=1)+'\n');print(json.dumps({'nodes':len(t['nodes']),'coordinate_basis':t['coordinate_basis'],'functional_gate_centres_changed':False,'scope':'source conversion only; re-predict before physical installation'}))
