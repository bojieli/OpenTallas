"""Derive RC wire terms from saved graphs. No NLDM interpolation/predict call.

Validate the same RC arithmetic against four already-saved baseline path terms.
Total/cell arrivals of the candidate are not reconstructed or invented.
"""
from pathlib import Path
import json,sys,collections
R=Path(sys.argv[1]);S=Path(sys.argv[2]);sys.path[:0]=[str(S/'results/core_lat_r8_1026')]
import l0r_r8_uf3 as A
old=json.loads((R/'baseline/plan_d1.json').read_text())[0];new=json.loads((R/'model_once/plan_model.json').read_text())[0];saved=json.loads((R/'model_once/result.json').read_text());fit=json.loads((R/'inputs/uf_phys3_v1.json').read_text());baseline=json.loads((R/'baseline/frozen_components.json').read_text())
for r in (old,new):
 for n in r['nodes_xy']:
  if n[3] not in A.U.SIZES:A.U.SIZES.append(n[3])
L=A.U.load_libs(R/'inputs/lib')
def derive(rec,co,params):
 P=A.PlanFromRecord(rec,str(R/'baseline/geo.txt'));wire={'root':0.};parts={};sinkvals={};means={};netdata={}
 todo=['root']
 for n in todo:
  todo.extend(P.kids.get(n,[]));node=P.nodes[n]
  if node['kind'] in ('leaf','macro'):
   pts=[node['xy']]+list(node['sinks']);edges=[(a,b,A.U.man(pts[a],pts[b])*params.get('kleaf',1.25))for a,b in A.U.mst_edges(pts)];cpin=node['cpin'][co]if'cpin'in node else A.U.FFC[co]
   cw,cp,el,rw=A.U.rc_tree(pts,edges,{i:cpin for i in range(1,len(pts))},A.U.R23,A.U.C23)
   vals=[wire[n]+params.get('bleaf',params.get('beta',1))*el[i]for i in range(1,len(pts))]
   sinkvals[n]=vals;means[n]=sum(vals)/len(vals);continue
  net=P.nets[n];pins={net['pin'][c]:L[co][P.nodes[c]['cell']]['cin']for c in P.kids[n]}
  cw,cp,el,rw=A.U.rc_tree(net['pts'],net['edges'],pins,A.U.R45,A.U.C45)
  netdata[n]=dict(pin_cap_ff=cp,wire_cap_ff=cw,net_length_um=sum(x[2]for x in net['edges']),hub_wire_ps=params.get('beta',1)*el[1]if len(el)>1 else 0)
  for c in P.kids[n]:
   w=params.get('beta',1)*el[net['pin'][c]];wire[c]=wire[n]+w;parts[c]=dict(driver=n,child=c,master=node['cell'],wire_ps=w,**netdata[n])
 return P,wire,parts,sinkvals,means,netdata
out=dict(scope='Static RC wire decomposition only; no new timing/model evaluation, NLDM interpolation, sizing or fitting',candidate_source='model_once saved immutable graph/result',corners={},baseline_controls=[])
for co,params in (('TT',fit['PMAX']),('FF',fit['PMIN'])):
 _,_,_,sv,_,_=derive(old,co,params)
 for key in ('sink_min','sink_max'):
  x=baseline['corners'][co][key];i=old['leaf_sinks'][x['leaf']].index(x['sink']);actual=sv[x['leaf']][i];expected=x['wire_total_ps'];assert abs(actual-expected)<1e-7,(co,key,actual,expected)
  out['baseline_controls'].append(dict(corner=co,path=key,wire_ps=actual,recorded_wire_ps=expected,match=True))
 P,wire,parts,sv,means,netdata=derive(new,co,params);lo=min(means,key=means.get);hi=max(means,key=means.get)
 span=means[hi]-means[lo];total=saved['corners'][co]['window'];bays=[]
 for prefix in ('Tpp','Tpq','Tpr','Tqp','Tqq','Tqr'):
  w=next(x for x in new['wire_paths']if x['edge']==prefix);driver=prefix+'_r%d'%(len(w['segs'])-2)if len(w['segs'])>1 else prefix+'_br'
  n=netdata[driver];bays.append(dict(bay=prefix,driver=driver,xy_um=w['paths'][-1][-1],wire_to_hub_ps=wire[driver]+n['hub_wire_ps'],**n))
 par={n[0]:n[1]for n in new['nodes_xy']};chain=[];u=hi
 while par[u] is not None:chain.append(parts[u]);u=par[u]
 out['corners'][co]=dict(total_saved_leaf_window_ps=total,wire_only_leaf_mean_min=dict(leaf=lo,wire_ps=means[lo]),wire_only_leaf_mean_max=dict(leaf=hi,wire_ps=means[hi]),wire_only_leaf_window_ps=span,cell_component_span_lower_bound_ps=max(0,total-span),bound='osc(cell)>=osc(total)-osc(wire); candidate min/max total leaf identities and cell slews were not retained by canonical summary helper, so exact cell paths are unavailable without a diagnostic replay',six_bay_wire_terms=bays,worst_wire_leaf_root_path=list(reversed(chain)))
D=R/'static_diagnosis';D.mkdir(exist_ok=True);(D/'wire.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({c:{k:x[k]for k in ('total_saved_leaf_window_ps','wire_only_leaf_window_ps','cell_component_span_lower_bound_ps','six_bay_wire_terms')}for c,x in out['corners'].items()},indent=2))
