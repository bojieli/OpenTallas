#!/usr/bin/env python3
"""Price actual negative TT paths against a pre-build named-sink clock plan.
Observed data delay held unchanged; no numerical timing or closure claim.
"""
import json,re,sys
from pathlib import Path
r=Path(sys.argv[1]);sys.path.insert(0,str(r/'src/results/core_lat_r8_1026'));sys.path.insert(0,str(r/'src/tools/die_plan'))
import l0r_r8_uf3 as A
from clock_model_cache import geometry_cache
U,V=A.U,A.V3
rec=json.load(open(r/'h0_family/dsdv_eng_rr_h0/plan_d1.json'))[0];fit=json.load(open(r/'src/results/model_refit3_1026/uf_phys3_v1.json'))
for c in sorted({n[3]for n in rec['nodes_xy']}):
 if c not in U.SIZES:U.SIZES.append(c)
p=A.PlanFromRecord(rec,str(r/'h0_family/dsdv_eng_rr_h0/geo.txt'));libs=U.load_libs(str(r/'lib'))
norm=lambda n:n.replace('\\','')
def predict(params,edge):
 detail={};V.predict3(p,libs,'TT',edge=edge,detail=detail,**params);out={}
 for node,v in detail.items():
  for name,arr in zip(rec['leaf_sinks'][node],v['sinks']):out[norm(name)]=arr
 return out
with geometry_cache(U):
 late=predict(fit['PMAX'],'rise');er=predict(fit['PMIN'],'rise');ef=predict(fit['PMIN'],'fall');early={k:min(er[k],ef[k])for k in er}
rows=[]
for part in (r/'h0_paths_original_tt.rpt').read_text().split('Startpoint: ')[1:]:
 lines=part.splitlines();sp=lines[0].strip();ep=next(l.split('Endpoint: ',1)[1].strip()for l in lines if l.startswith('Endpoint: '));sk=norm(sp+'/CLK');ek=norm(ep+'/CLK')
 if sk not in late or ek not in early:continue
 def ck_time(pin):
  line=next(l for l in lines if (' '+pin+' ')in l);before=re.split(r'\s[\^v]\s',line)[0];return float(before.split()[-1])
 src=ck_time(sp+'/CLK');dst=ck_time(ep+'/CLK')-833
 data=float(next(l for l in lines if 'data arrival time'in l).split()[0]);logic=data-src
 lib=float(next(l for l in lines if 'library setup time'in l).split()[0])
 cppr=float(next(l for l in lines if 'clock reconvergence pessimism'in l).split()[0])
 oldslack=float(next(l for l in lines if 'slack ('in l).split()[0])
 damage=late[sk]-early[ek];price=833-60+lib+cppr-logic-damage
 rows.append(dict(source=sp,capture=ep,old_slack_ps=oldslack,old_clock_damage_ps=src-dst,old_observed_logic_ps=logic,predicted_clock_damage_ps=damage,predicted_slack_data_unchanged_ps=price,predicted_launch_ps=late[sk],predicted_capture_ps=early[ek]))
out=dict(scope='Pre-build model on actual named sinks; observed data delay and old CPPR held unchanged, no closure claim',clock_plan=rec['name'],rows=rows)
json.dump(out,open(r/'h0_path_price.json','w'),indent=1);print(json.dumps(out,indent=1))
