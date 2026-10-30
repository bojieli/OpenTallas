"""Joint TT/FF geometry/NLDM prediction for natural A0 domains. No measured arrivals."""
import sys,json,statistics
from pathlib import Path
p=Path.cwd();root=p/'natural_model';sys.path.insert(0,str(p/'src'));sys.path.insert(0,str(root/'tools'))
source,census,kit,out=sys.argv[1:]
sys.argv=['qualify2.py',source,census,kit,'unused','unused'];env={'__file__':str(p/'src/qualify2.py')}
# Its data parser adds its historical snapshot first; explicitly replace only
# that import path with this isolated electrical compiler snapshot.
s=(p/'src/qualify2.py').read_text().split('model=M.predict_tree')[0].replace("str(Path('tool_snapshot/tools/die_plan').resolve())","str(Path('natural_model/tools').resolve())")
exec(s,env);sl=env['sl'];M=env['M'];assert sl.get('clock_sink_points_um'), 'public A0 model requires explicit actual clock ITerm sink points';entry=sl['clock_entry_wire'];first=next(n for n in sl['core_tree']['nodes']if n['name']==entry['first_buffer']);q=entry['public_pin'];length=abs(q['x']-first['xy_um'][0])+abs(q['y']-first['xy_um'][1]);model=None
for corner in ('TT','FF'):
 cap=env['libs'][corner][first['master']]['cap'];elmore=length*(.018515*.8)*(length*(.17137*.9)/2+cap);input_slew=(20.**2+(2.2*elmore)**2)**.5
 one=M.predict_tree(sl,{corner:env['libs'][corner]},env['pts'],env['caps'],.018515*.8,.17137*.9,input_slew_ps=input_slew)
 if model is None:model=dict(one);model['corners']={}
 row=one['corners'][corner]
 for key in ('min_ps','mean_ps','max_ps'):row[key]+=elmore
 for net in row['nets']:net['input_arrival_ps']+=elmore
 for leaf in row['leaf_means']:
  for key in ('min_ps','mean_ps','max_ps'):leaf[key]+=elmore
 row['entry_wire_model']=dict(public_pin=q,first_buffer=first['name'],first_xy_um=first['xy_um'],wire_um=length,wire_r_kohm_um=.018515*.8,wire_c_ff_um=.17137*.9,input_cap_ff=cap,elmore_ps=elmore,input_slew_ps=input_slew,scope='passive source-to-first-buffer wire included; planned M4 access stack is not routed signoff')
 model['corners'][corner]=row
model['basis']+='; explicit public E/M4 entry passive wire + real buffered feed'
model['leaf_sink_points_basis']=sl['clock_sink_points_source']
model['buffer_wire_points_basis']='shared estimator canonical buffer-cell-centre convention'
t=sl['core_tree'];leafmap={l['node']:l for l in t['leaves']};domainmap={n:g['name']for g in sl['electrical_domain_plan']for n in g['leaf_nodes']};domains={};corners={}
for c,row in model['corners'].items():
 vals=[];dm={}
 for l in row['leaf_means']:
  leaf=leafmap[l['node']];ins=leaf.get('early_tap_ps',{}).get(c,dict(min=0,max=0));effective=dict(min=l['min_ps']+ins['min'],max=l['max_ps']+ins['max'],mean=l['mean_ps']+(ins['min']+ins['max'])/2)
  leaf.setdefault('pin_latency_ps',{})[c]=dict(min=l['min_ps'],max=l['max_ps']);vals.append(effective)
  dm.setdefault(domainmap[l['node']],[]).append(effective)
 domains[c]={n:dict(min=min(v['min']for v in vs),max=max(v['max']for v in vs),mean=statistics.mean(v['mean']for v in vs),leaf_mean_window=max(v['mean']for v in vs)-min(v['mean']for v in vs))for n,vs in dm.items()}
 corners[c]=dict(leaf_min=min(v['min']for v in vals),leaf_max=max(v['max']for v in vals),leaf_window=max(v['max']for v in vals)-min(v['min']for v in vals),slew_max=row['slew_max_ps'])
report=dict(scope='UNBALANCED NATURAL TREE MODEL ONLY - domain trunks remain to size',basis=model['basis'],measured_timing_used=False,corners=corners,domains=domains,clock_nodes=len(t['nodes']))
Path(out+'_model.json').write_text(json.dumps(model,indent=1)+'\n');Path(out+'_report.json').write_text(json.dumps(report,indent=1)+'\n');Path(out+'_pins.json').write_text(json.dumps(sl,indent=1)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='domains'}),flush=True)
