import json,gzip,collections,statistics,hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);o=Path(sys.argv[2]);d=json.load(gzip.open(p,'rt'))
ports={x['pin']:x for x in d['port_bits']};seq={x['instance']:x for x in d['sequential_instances']}
ranges={'o_next':[2.16,52.16],'o_grp_h':[52.4,54.4],'pc__fo':[54.64,54.84],'i_next':[55.08,187.08],'x__est__0_1':[187.32,187.52],'pc__ki':[187.76,193.36],'i_grp':[193.6,199.2],'i_grp_h':[199.44,215.34],'o_grp':[215.58,264.98]}
newports={k:list(v['xy_um']) for k,v in ports.items()};groupcounts={}
for name,(lo,hi) in ranges.items():
 ps=sorted([v for v in ports.values() if v['base_port']==name],key=lambda x:x['xy_um'][0]);groupcounts[name]=len(ps)
 assert all(v['actual_nearest_face']=='N' for v in ps)
 for i,v in enumerate(ps):newports[v['pin']]=[lo+(i+.5)*(hi-lo)/len(ps),v['xy_um'][1]]
def nearest(x):
 a,b=x;return min({'W':a,'E':267.84-a,'S':b,'N':300.24-b},key=lambda k:{'W':a,'E':267.84-a,'S':b,'N':300.24-b}[k])
newff={};ledger=[]
for s in seq.values():
 points=s['output_pins'] or s['input_pins'];old=points[0]['xy_um'];face=nearest(old)
 pp=[v for v in s['direct_input_port_bits']+s['direct_output_port_bits'] if ports[v]['actual_nearest_face']==face]
 if not pp:continue
 delta=[statistics.median(newports[v][i]-ports[v]['xy_um'][i] for v in pp) for i in [0,1]]
 if any(abs(x)>1e-7 for x in delta):
  newff[s['instance']]=[old[i]+delta[i] for i in [0,1]];ledger.append({'instance':s['instance'],'old_xy':old,'target_xy':newff[s['instance']],'same_face_obligations':pp,'delta':delta})
def xy(v):
 if v.get('instance') in newff:
  s=seq[v['instance']];old=(s['output_pins'] or s['input_pins'])[0]['xy_um'];return [v['xy_um'][i]+newff[v['instance']][i]-old[i] for i in [0,1]]
 if v.get('pin') in newports and 'instance' not in v:return newports[v['pin']]
 return v['xy_um']
counts=collections.Counter();bad=[];mx={}
def edge(a,b,k):
 aa,bb=xy(a),xy(b);r=sum(abs(x-y) for x,y in zip(aa,bb));counts[k]+=1;mx[k]=max(mx.get(k,0),r)
 if r>405+1e-8:bad.append({'root':a['name'],'sink':b['name'],'root_xy':aa,'sink_xy':bb,'L1_um':r,'category':k})
for e in d['data_stage_edges']:edge(e['root'],e['endpoint'],'data')
for e in d['output_port_sources']:
 for a in e['roots']:edge(a,ports[e['port']],'output_port')
for s in seq.values():
 for e in s['input_pins']:
  if e['kind'] not in ['data_next_state','memory_data_control']:
   for a in e['roots']:edge(a,e,'async_other_control')
bad.sort(key=lambda x:-x['L1_um'])
r={'scope':'MODEL ONLY coordinate-target overlay of actual connected normalPC6 PRECTS graph; same source/clock/portfaces/outline, reorder N bus pin ranges. No RTL/kit edits, no legal packing/clock/finalreach/adoption claim.','identity_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'odb_sha256':d['odb_sha256'],'new_N_ranges':ranges,'group_counts':groupcounts,'projected_group_flops_per_um':{n:groupcounts[n]/(r[1]-r[0]) for n,r in ranges.items()},'moved_ff_targets':len(newff),'pairs':sum(counts.values()),'over405':len(bad),'max_L1_by_category':mx,'worst20':bad[:20],'all_violations':bad,'FF_target_ledger':ledger,'port_target_ledger':[{'port':v,'xy':xy} for v,xy in newports.items() if xy!=ports[v]['xy_um']]}
(o/'pinrange_model.json.gz').write_bytes(gzip.compress((json.dumps(r,separators=(',',':'))+'\n').encode(),mtime=0));print(json.dumps({k:r[k] for k in ['moved_ff_targets','pairs','over405','max_L1_by_category','worst20']},indent=2))
