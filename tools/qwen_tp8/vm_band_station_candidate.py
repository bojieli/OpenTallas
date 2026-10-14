#!/usr/bin/env python3
"""Slot-based control station candidate graph using real fan pins and TT sides.
Source entries/column consumers/gather ABI remain unassigned; no route is implied.
"""
import argparse,collections,hashlib,json,math
from pathlib import Path
from vm_lef_pins import read
from vm_band_pair import timing
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'results/arch/qwen_tp8_1012'
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--joint-geometry',type=Path);args=ap.parse_args()
 comp=json.loads((A/'vm_band_composition_codex.json').read_text());packet=json.loads((A/'vm_band_boundary_packet_codex.json').read_text());pool=packet['spare_slots'];cols=sorted((c for c in comp['children']if c['inst'].startswith('u_c')),key=lambda c:int(c['inst'][3:]));x0,y0=comp['origin_um']
 if args.joint_geometry:
  joint=json.loads(args.joint_geometry.read_text());reserved={(c['candidate_destination']['bay'],c['candidate_destination']['slot'])for c in joint['candidate_children']if 'candidate_destination'in c}
  pool=[s for s in pool if (s['bay'],s['slot'])not in reserved]
 free=set(range(len(pool)));stations=[]
 for col,c in enumerate(cols):
  cx=x0+c['at'][0]+c['outline_um'][0]/2;cy=y0+c['at'][1]+c['outline_um'][1]/2
  i=min(free,key=lambda i:abs(pool[i]['at'][0]+6.48-cx)+abs(pool[i]['at'][1]+33.48-cy));free.remove(i)
  stations.append(dict(column=col,slot=pool[i],source_entry='UNASSIGNED',consumer_pins='UNASSIGNED'))
 bundle=[]
 for master,width,dy in [('pc',20,0),('lc',28,19.44),('lc',28,38.88),('me',1,58.32)]:
  view=f'physical/ref_tile/qfd_vm_fan_{master}/views/ot_qfd_vm_fan_t';f=next((ROOT/view).glob('*.lef'));pins=read(f)[1];m,refs=timing(view);bits=[]
  for bit in range(width):
   lp=m[f'q[{bit}]'];cp=m[f'd[{bit}]'];lr=refs[lp['clk'][0]];cr=refs[cp['clk'][0]];o=lp['out']+lr['bmax']-lr['rise'];ss=cp['inp']+cr['rise']-cr['bmin'];reach=min(500,(833.3333333333-210-o-ss)/.76)-.2
   bits.append(dict(bit=bit,A=[pins[f'q[{bit}]']['x'],pins[f'q[{bit}]']['y']+dy],B=[pins[f'd[{bit}]']['x'],pins[f'd[{bit}]']['y']+dy],reach_um=reach))
  bundle.append(dict(master=master,width=width,at_relative_um=[0,dy],bits=bits))
 graph={i:[]for i in range(32)};links=[]
 for a in range(32):
  ax,ay=stations[a]['slot']['at']
  for b in range(32):
   if a==b:continue
   bx,by=stations[b]['slot']['at'];margin=math.inf
   for fan in bundle:
    for z in fan['bits']:
     d=abs(ax+z['A'][0]-bx-z['B'][0])+abs(ay+z['A'][1]-by-z['B'][1]);margin=min(margin,z['reach_um']-d)
   if margin>=0:graph[a].append(b);links.append(dict(source=a,destination=b,worst_TT_reach_margin_um=round(margin,4)))
 def bfs(root):
  ds={root:0};prev={};queue=collections.deque([root])
  while queue:
   a=queue.popleft()
   for b in graph[a]:
    if b not in ds:ds[b]=ds[a]+1;prev[b]=a;queue.append(b)
  return ds,prev
 opts=[]
 for root in range(32):
  ds,prev=bfs(root)
  if len(ds)==32:opts.append((max(ds.values()),sum(ds.values()),root,ds,prev))
 best=min(opts)if opts else None
 if best:
  depth,_,root,ds,prev=best
  schedule=dict(candidate_internal_root_column=root,source_to_root_enabled_edges='UNASSIGNED',max_internal_hops=depth,
    hops_by_column=ds,tree_parent=prev,equalized_additional_enabled_edges_by_column={i:depth-d for i,d in ds.items()},
    station_local_unshared_equalization_fan_tiles=3*sum(depth-d for d in ds.values()),equalization_alternatives='Shared delay branches or wider delay tiles can change this count; no packing claim',
    ME_free_edges='must equalize separately to all payload/fill capture events; no core_step gating of loader')
 else:schedule=dict(status='NO_FULL_REACH_GRAPH')
 candidate_edges=[]
 if best:
  for child,parent in schedule['tree_parent'].items():
   ax,ay=stations[parent]['slot']['at'];bx,by=stations[child]['slot']['at']
   for fi,fan in enumerate(bundle):
    for bit in fan['bits']:
     candidate_edges.append(dict(kind='candidate_station_control',source_column=parent,destination_column=child,fan=fi,bit=bit['bit'],A=[ax+bit['A'][0],ay+bit['A'][1]],B=[bx+bit['B'][0],by+bit['B'][1]],pair_reach_um=bit['reach_um']))
 out=dict(schema='opentallas.qwen.vm-band-control-station-candidate.v1',qualification=False,status='CANDIDATE_SLOT_GRAPH_NOT_ASSIGNED',
  actual_PG_usable_fraction=1-json.loads((A/'vm_cluster_layer_grant_1013.json').read_text())['die_pg']['combined_track_fraction'],
  setup_reserve_ps=210,station_count=32,spare_slot_count=len(pool),unassigned_remaining_whole_slots=len(free),
  candidate_control_edges=candidate_edges,station_fan_shapes=[{k:v for k,v in b.items()if k!='bits'}for b in bundle],stations=stations,actual_TT_valid_station_links=links,schedule=schedule,
  caveats=['Station slots are greedy alternatives; they may conflict with boundary-extension or gather candidates.','Real source entry/column fanout/gather pins not assigned; this graph only checks all actual station fan d/q bits.','Existing logical3levels cannot replace graph hop schedule; source phases/epochs/ME require re-alignment and full bench.','Local epoch16 opaque dictionary versus direct21 request/capture/drain costs remain conditional.','No combined route cut or SS/hold/clock entry classification proof.'])
 (A/('vm_band_station_joint_candidate_codex.json' if args.joint_geometry else 'vm_band_station_candidate_codex.json')).write_text(json.dumps(out,indent=1)+'\n');print(dict(graph_edges=len(links),schedule=schedule))
if __name__=='__main__':main()
