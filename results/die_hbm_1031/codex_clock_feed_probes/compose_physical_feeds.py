"""Piecewise routed HBM clock proof at actual die feed nodes and physical hub roots.
Inputs: matched source-load calibrated bridges + matched-waveform routed mesh records.
This is prototype timing evidence; joint die+hub route and real kit views remain required.
"""
from pathlib import Path
import json,re,sys,shutil,collections
src,data,choice,out=sys.argv[1:5];src,data,out=Path(src),Path(data),Path(out);out.mkdir(exist_ok=True,parents=True)
receipts=json.load(open(data/'physical_feed_receipts.json'))
def load_rows(p):
 return {(f[1],f[0]):list(map(float,f[2:8])) for l in p.read_text().splitlines() if (f:=l.split())}
for c in ('TT','FF'):
 p=json.load(open(src/f'tap_arrivals_{c}.json'))
 for side,reg,origin,root in [('NW','T028',[5140.8,6065.28],[4296.276,1468.8]),('NE','T029',[15042.24,6065.28],[3764.916,630.72])]:
  name=side+'_'+choice;f=receipts[name];q=f['corners'][c];part=side+'_hub';d=data/'matched_mesh'/name
  rec=json.load(open(d/'rec_drt.json'));fr=json.load(open(d/'rec_drt_fall.json'));m=json.load(open(d/f'mc_{c}.json'));fm=json.load(open(d/f'fall_{c}.json'));rows=load_rows(d/f'both_{c}.txt')
  def port(n):
   if n=='L_clk':return f't_{part}__clk'
   z=re.fullmatch(r'(?:L|K)_clk_(t\d+|c\d+)',n)
   if z is None:raise ValueError(n)
   return f't_{part}__clk_{z[1]}'
  rv={port(n):v for n,v in zip(m['loads'],m['routed'])};fv={port(n):v for n,v in zip(fm['loads'],fm['routed'])};mesh_ports=set(rv)
  for t in rec.get('early_taps',[]):rv[port(t['port'])]=t['arr'][c]['late']
  for t in fr.get('early_taps',[]):fv[port(t['port'])]=t['arr'][c]['late']
  taps=[t for t in p['taps'] if t['part']==part];assert set(rv)=={t['port'] for t in taps}==set(fv)
  paths=[k for k,v in p['node_cell'].items() if k.startswith('h') and v==f['source']];assert len(paths)==1,paths
  feed=paths[0];base=p['node_late_ps'][feed]+q['rise_late_delta_ps'];be=p['node_early_ps'][feed]+q['rise_early_delta_ps'];bf=p['node_fall_late_ps'][feed]+q['fall_late_delta_ps'];bfe=p['node_fall_early_ps'][feed]+q['fall_early_delta_ps'];depth=p['node_stages'][feed]+int(f['source_inverted'])
  root_path=feed+chr(0x700);assert root_path not in p['node_cell']
  def node(path,cell,xy,stages,late,early,fall,fall_early):
   p['node_cell'][path]=cell;p['node_xy_um'][path]=xy;p['node_stages'][path]=stages;p['node_late_ps'][path]=late;p['node_early_ps'][path]=early;p['cppr_node_range_ps'][path]=late-early;p['node_fall_late_ps'][path]=fall;p['node_fall_early_ps'][path]=fall_early
  node(root_path,part+'/root',[a+b for a,b in zip(origin,root)],depth,base,be,bf,bfe)
  by={n['tag']:n for n in rec['nodes']};children=collections.defaultdict(list)
  for n in rec['nodes']:children[n['parent']].append(n['tag'])
  chain=[];tag=rec['root']
  while True:
   chain.append(by[tag])
   if len(children[tag])!=1:break
   tag=children[tag][0]
  path=root_path;root_buffer_path=None
  for n in chain:
   path+=chr(0x100);v=rows[(n['tag'],'Y')]
   node(path,part+'/'+n['tag'],[origin[i]+n['xy'][i] for i in (0,1)],depth+n['depth'],base+v[0],be+v[1],bf+v[3],bfe+v[4])
   if root_buffer_path is None:root_buffer_path=path
  for t in taps:
   n=t['port'];t.update(late_ps=base+rv[n],early_ps=be+rv[n],fall_late_ps=bf+fv[n],fall_early_ps=bfe+fv[n],tree_path=path if n in mesh_ports else root_buffer_path,stages_from_root=depth+len(chain) if n in mesh_ports else depth+1)
   # Keep cppr_node as region identity; real shared-node credit is computed from tree_path.
   t['hub_mesh']=dict(mesh_ps=rv[n],mesh_fall_ps=fv[n],entry_node=root_path,source_feed_node=feed,source_feed_cell=f['source'],root_rise_ps=base,root_fall_ps=bf,root_xy_um=[a+b for a,b in zip(origin,root)],choice=choice,stage='DRT mesh, matched root waveform; GRT die source + DRT calibrated local bridge')
  print(c,part,'feed',f['source'],'root',round(base,2),'mesh',round(min(rv.values()),2),round(max(rv.values()),2),'prefix',','.join(n['tag'] for n in chain))
 p['basis']+=' | CODEX physical-feed '+choice+': actual C12e source nodes + calibrated routed bridge + matched-waveform DRT mesh; actual shared premesh prefix only; region IDs retained; fall uses measured tree fall and existing linear Thevenin model'
 p['physical_feed_scope']='Prototype piecewise evidence. Joint die+hub route/island binding, new root geometry and real signed core views still gate G4; full hub V2 mesh DRC remains nonzero.'
 json.dump(p,open(out/f'tap_arrivals_{c}.json','w'))
for n in ('mesh.json','droop_regions.json'):
 if (src/n).exists():shutil.copy(src/n,out/n)
