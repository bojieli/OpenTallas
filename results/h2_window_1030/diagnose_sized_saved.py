"""Saved final timing traces + static RC only; no new predict/interp call."""
from pathlib import Path
import json,sys
R=Path(sys.argv[1]);S=Path(sys.argv[2])
# Reuse only reconstruction and static RC helpers; stop before their report loop.
source=(R/'static_wire_diagnosis.py').read_text().split('out=dict(scope=')[0]
exec(compile(source,'static_RC_helpers','exec'),globals())
rec=json.loads((R/'final_model/plan_model.json').read_text())[0]
tr=json.loads((R/'final_model/timing_traces.json').read_text());result=json.loads((R/'final_model/result.json').read_text());par={n[0]:n[1]for n in rec['nodes_xy']}
out=dict(scope='Saved final model traces plus exact static RC only, no new timing/kernel run',corners={})
for co,params,edges in [('TT',fit['PMAX'],['rise']),('FF',fit['PMIN'],['rise','fall'])]:
 P,wire,parts,sv,means,netdata=derive(rec,co,params)
 runs={e:tr[co+'_'+e]for e in edges}
 leafvals={n:min((v['leaves'][n],e)for e,v in runs.items())for n in rec['leaf_sinks']}
 paths={}
 for label,leaf in [('min',min(leafvals,key=lambda n:leafvals[n][0])),('max',max(leafvals,key=lambda n:leafvals[n][0]))]:
  value,edge=leafvals[leaf];a=runs[edge]['node_arrival_slew'];chain=[];u=leaf
  while par[u]is not None:
   p=par[u];w=parts[u]['wire_ps'];chain.append(dict(driver=p,child=u,master=P.nodes[p]['cell'],cell_ps=a[u][0]-a[p][0]-w,wire_ps=w,driver_slew_ps=a[p][1],**netdata[p]));u=p
  tailwire=means[leaf]-wire[leaf];tailcell=value-a[leaf][0]-tailwire
  chain=list(reversed(chain))+[dict(driver=leaf,child='leaf_mean',master=P.nodes[leaf]['cell'],cell_ps=tailcell,wire_ps=tailwire,driver_slew_ps=a[leaf][1])]
  ct=sum(x['cell_ps']for x in chain);wt=sum(x['wire_ps']for x in chain);assert abs(ct+wt-value)<1e-7
  paths[label]=dict(leaf=leaf,edge=edge,total_ps=value,native_input_ps=result['native_input']['arrival_ps'][co],cell_ps=ct,wire_ps=wt,path=chain)
 bays=[]
 for prefix in ['Tpp','Tpq','Tpr','Tqp','Tqq','Tqr']:
  w=next(x for x in rec['wire_paths']if x['edge']==prefix);driver=prefix+'_r%d'%(len(w['segs'])-2)if len(w['segs'])>1 else prefix+'_br'
  vals=[]
  for e,v in runs.items():
   a=v['node_arrival_slew'];child=P.kids[driver][0];cd=a[child][0]-a[driver][0]-parts[child]['wire_ps'];hubwire=wire[driver]+netdata[driver]['hub_wire_ps'];hubtotal=a[driver][0]+cd+netdata[driver]['hub_wire_ps']
   vals.append(dict(edge=e,arrival_to_hub_ps=hubtotal,wire_to_hub_ps=hubwire,cell_to_hub_ps=hubtotal-hubwire,driver_slew_ps=a[driver][1],**netdata[driver]))
  chosen=min(vals,key=lambda q:q['arrival_to_hub_ps']);bays.append(dict(bay=prefix,driver=driver,early_corner=chosen,edge_runs=vals))
 out['corners'][co]=dict(critical_leaf_mean_paths=paths,total_span_ps=paths['max']['total_ps']-paths['min']['total_ps'],critical_cell_delta_ps=paths['max']['cell_ps']-paths['min']['cell_ps'],critical_wire_delta_ps=paths['max']['wire_ps']-paths['min']['wire_ps'],six_bay_hub_arrivals=bays)
(R/'final_model/saved_diagnosis.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({c:{k:v for k,v in q.items()if k not in ('critical_leaf_mean_paths','six_bay_hub_arrivals')}for c,q in out['corners'].items()},indent=2))
