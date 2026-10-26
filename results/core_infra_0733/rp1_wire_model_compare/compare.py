import json,copy
from pathlib import Path
import core_infra_plan as CP
p=Path('.');data=json.load(open('input.json'));sl=json.load(open('slice.json'));geo=Path('geo.txt').read_text();rects=[list(map(float,f[3:7])) for l in geo.splitlines() if (f:=l.split())[0]=='MACRO'];rc4=[.0180365/2,.1275*1.1];rc5=[.0189935/2,.098*1.1]
def profile(h,v,obs=(),vobs=()):return dict(horizontal_rc=h,vertical_rc=v,obstacles=obs,vertical_obstacles=vobs,clearance=0.)
m4obs=[[r[0]+.072,r[1],r[2]-.072,r[3]] for r in rects]
trunk=profile(rc4,rc5,m4obs);lower=profile([.0297127,.1675],[.031287,.1315],rects,rects)
macro={l['node']:trunk for l in sl['core_tree']['leaves'] if l.get('load_class')=='macro'}
for mode,leaf in [('actual_leaf_layer_prototype',lower),('forced_all_M4_M5_unimplemented',trunk),('M6_M5_unimplemented_capacity_unreserved',profile([.0118796/2,.1305*1.1],rc5))]:
 model=dict(nonleaf=trunk,leaf=leaf,nodes=macro)
 try:
  result=CP.predict_tree(sl,data['libraries'],data['points'],data['caps'],0,0,input_slew_ps=0,routing_model=model)
  result['qualification']='CONDITIONAL PROTOTYPE; actual per-corner caps, ownmacrobranchM4profileexplicit, sharedMSTpathsnotmerged, no via/coupling/capacity/extractedNDRC; no candidate design or route'
 except ValueError as e:result=dict(verdict='MODEL_INCOMPLETE_FAIL_CLOSED',reason=str(e))
 (p/(mode+'.json')).write_text(json.dumps(result,indent=1));print(mode,{c:{k:round(v,2) for k,v in x.items() if k in ('mean_ps','window_ps')} for c,x in result.get('corners',{}).items()} or result,flush=True)
