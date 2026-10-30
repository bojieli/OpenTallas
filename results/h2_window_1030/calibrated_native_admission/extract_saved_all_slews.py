"""Extract all-buffer slew from saved states, no new timing/propagation run.

Internal output transitions are algebraically recovered from every child input
and original RC/gslew, checked against all children. Leaf outputs alone require
reconstructing the original NLDM output-transition query at the FIXED saved
input slew and FIXED original load; no new delay/arrival is propagated.
"""
from pathlib import Path
import json,math,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2]);sub=sys.argv[3]if len(sys.argv)>3 else'final_model'
source=(R/'static_wire_diagnosis.py').read_text().split('out=dict(scope=')[0];exec(compile(source,'static_RC_helpers','exec'),globals())
rec=json.loads((R/sub/'plan_model.json').read_text())[0];tr=json.loads((R/sub/'timing_traces.json').read_text());result=json.loads((R/sub/'result.json').read_text());P=A.PlanFromRecord(rec,str(R/'baseline/geo.txt'));out=dict(scope='Saved FIXED-state all-buffer slew extraction; no new predictor/clock-arrival/kernel run',records={},corners={})
for co,params,edges in [('TT',fit['PMAX'],['rise']),('FF',fit['PMIN'],['rise','fall'])]:
 _,_,parts,_,_,_=derive(rec,co,params);allrows=[]
 for edge in edges:
  saved=tr[co+'_'+edge]['node_arrival_slew'];rows={};sk='trise'if edge=='rise'else'tfall';dk='rise'if edge=='rise'else'fall'
  for u,n in P.nodes.items():
   s0=saved[u][1]
   if u in P.kids:
    reconstructed=[]
    for child in P.kids[u]:
     el=parts[child]['wire_ps']/params['beta'];residual=saved[child][1]**2-(params['gslew']*el)**2
     assert residual>=-1e-6,(co,edge,u,residual)
     reconstructed.append(math.sqrt(max(0.,residual)))
    assert max(reconstructed)-min(reconstructed)<1e-5,(co,edge,u,reconstructed)
    so=reconstructed[0];basis='algebraic inversion of exact saved child input and originalRC'
   else:
    pts=[n['xy']]+list(n['sinks']);es=[(a,b,A.U.man(pts[a],pts[b])*params['kleaf'])for a,b in A.U.mst_edges(pts)];cp=n['cpin'][co]if'cpin'in n else A.U.FFC[co]
    cw,cp,el,rw=A.U.rc_tree(pts,es,{i:cp for i in range(1,len(pts))},A.U.R23,A.U.C23);lc=L[co][n['cell']]
    shield=A.U._shield(lc,dk,s0,cw+cp,rw);ceff=cp+cw*(1-params['alpha']*shield);so=A.U.interp(lc[sk],s0,ceff);basis='original leaf transition table at fixed saved input/load, no new arrival'
   assert math.isfinite(s0)and math.isfinite(so)
   rows[u]=dict(master=n['cell'],kind=n['kind'],input_ps=s0,output_ps=so,basis=basis)
  assert len(rows)==1811
  leafmax=max(rows[u]['output_ps']for u in rows if u not in P.kids)
  allrows.extend((u,edge,v)for u,v in rows.items());out['records'][co+'_'+edge]=rows
  # Summary rounds leaf outputs across bothFFedges; retain exact reconstruction.
  assert leafmax<=result['corners'][co]['leaf_out_slew_max']+.0051
  if co=='TT':assert abs(round(leafmax,2)-result['corners'][co]['leaf_out_slew_max'])<.001
 mi=max(allrows,key=lambda z:z[2]['input_ps']);mo=max(allrows,key=lambda z:z[2]['output_ps'])
 violations=[dict(node=u,edge=e,**v)for u,e,v in allrows if v['input_ps']>80 or v['output_ps']>80]
 out['corners'][co]=dict(buffers_per_edge=1811,edges=edges,max_input=dict(node=mi[0],edge=mi[1],ps=mi[2]['input_ps']),max_output=dict(node=mo[0],edge=mo[1],ps=mo[2]['output_ps']),violations=violations,all_buffer_slew80=not violations)
out['verdict']='PASS'if all(q['all_buffer_slew80']for q in out['corners'].values())else'HOLD outside all-buffer80ps calibration'
(R/sub/'all_buffer_slew.json').write_text(json.dumps(out)+'\n');summary={k:v for k,v in out.items()if k!='records'};(R/sub/'all_buffer_slew_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
