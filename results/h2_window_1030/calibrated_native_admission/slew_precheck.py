"""Whole-trace transition-only calibration precheck, no arrival/delay run.

Uses stock UF3 actualRC, shielding and transition tables at TT/FF. No predict3,
calibrated_summary, sizing, fitting or clock-arrival propagation is invoked.
"""
from pathlib import Path
import json,math,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2]);D=R/'tpqt_slew_geometry';sys.path[:0]=[str(S/'results/core_lat_r8_1026')]
import l0r_r8_uf3 as A
r=json.loads((D/'plan_geometry.json').read_text())[0];sl=json.loads((D/'slice_geometry_native.json').read_text());fit=json.loads((R/'inputs/uf_phys3_v1.json').read_text())
for c in r['frozen_masters'].values():
 if c not in A.U.SIZES:A.U.SIZES.append(c)
L=A.U.load_libs(R/'inputs/lib');P=A.PlanFromRecord(r,str(R/'baseline/geo.txt'));root=next(q['xy_um']for q in sl['core_tree']['nodes']if q['name']=='mp_ck_root');length=A.U.man(root,r['native_input']['xy_um']);out=dict(scope='Transition-only all-buffer calibration precheck; no new delay/arrival kernel',corners={},records={})
for co,params,edges in [('TT',fit['PMAX'],['rise']),('FF',fit['PMIN'],['rise','fall'])]:
 rows_all=[]
 for edge in edges:
  root_s=2.2*A.U.R45*length*(A.U.C45*length/2+L[co][P.nodes['root']['cell']]['cin']);inputs={'root':root_s};order=['root'];rows={};dk='rise'if edge=='rise'else'fall';sk='trise'if edge=='rise'else'tfall'
  for u in order:
   n=P.nodes[u];s0=inputs[u];lc=L[co][n['cell']]
   if u not in P.kids:
    pts=[n['xy']]+list(n['sinks']);es=[(a,b,A.U.man(pts[a],pts[b])*params['kleaf'])for a,b in A.U.mst_edges(pts)];cp=n['cpin'][co]if'cpin'in n else A.U.FFC[co];cw,cp,el,rw=A.U.rc_tree(pts,es,{i:cp for i in range(1,len(pts))},A.U.R23,A.U.C23)
   else:
    net=P.nets[u];cw,cp,el,rw=A.U.rc_tree(net['pts'],net['edges'],{net['pin'][kid]:L[co][P.nodes[kid]['cell']]['cin']for kid in P.kids[u]},A.U.R45,A.U.C45)
   shield=A.U._shield(lc,dk,s0,cw+cp,rw);ceff=cp+cw*(1-params['alpha']*shield);so=A.U.interp(lc[sk],s0,ceff)
   assert math.isfinite(s0)and math.isfinite(so)
   rows[u]=dict(master=n['cell'],input_ps=s0,output_ps=so,pin_cap_ff=cp,wire_cap_ff=cw,effective_cap_ff=ceff)
   for kid in P.kids.get(u,[]):inputs[kid]=math.hypot(so,params['gslew']*el[net['pin'][kid]]);order.append(kid)
  assert len(rows)==1811
  out['records'][co+'_'+edge]=rows;rows_all.extend((u,edge,q)for u,q in rows.items())
  bad=[dict(node=u,edge=e,**q)for u,e,q in rows_all if q['input_ps']>80 or q['output_ps']>80]
  mi=max(rows_all,key=lambda x:x[2]['input_ps']);mo=max(rows_all,key=lambda x:x[2]['output_ps'])
  out['corners'][co]=dict(max_input=dict(node=mi[0],edge=mi[1],ps=mi[2]['input_ps']),max_output=dict(node=mo[0],edge=mo[1],ps=mo[2]['output_ps']),violations=bad,all_buffer80=not bad)
# Every node outside the changed Tpqt branch must reproduce the saved fixed
# state exactly. This checks the transition-only implementation without a
# duplicate baseline predictor run.
par={n[0]:n[1]for n in r['nodes_xy']}
def affected(u):
 while u is not None:
  if u=='Tpqt_br':return True
  u=par[u]
 return False
baseline=json.loads((R/'final_model/all_buffer_slew.json').read_text())
comparison=[]
for tag,rows in out['records'].items():
 for u,q in rows.items():
  if not affected(u):
   for key in ['input_ps','output_ps']:
    delta=abs(q[key]-baseline['records'][tag][u][key]);assert delta<1e-5,(tag,u,key,delta)
   comparison.append((tag,u))
out['unchanged_saved_state_control']=dict(records=len(comparison),tolerance_ps=1e-5,verdict='PASS')
out['verdict']='PASS'if all(q['all_buffer80']for q in out['corners'].values())else'HOLD'
(D/'slew_precheck.json').write_text(json.dumps(out)+'\n');summary={k:v for k,v in out.items()if k!='records'};(D/'slew_precheck_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
