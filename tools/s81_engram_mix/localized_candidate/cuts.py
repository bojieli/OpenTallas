#!/usr/bin/env python3
"""Conditional M4/M5 cut screen using actual track offsets and explicit channels."""
import argparse,json,re,subprocess,math
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();R=Path(__file__).resolve().parents[3];O=a.out
j=json.loads((O/'connected_geometry.json').read_text());q=j['results']['Q_cooptimized_capsules'];boxes=q['placement'];obs={}
for master,v in j['leaf_views'].items():
 s=subprocess.check_output(['git','show',v['record']+':'+v['path']],cwd=R,text=True);body=s.split('\n  OBS\n',1)[1];layer=None;rr=[]
 for line in body.splitlines():
  if m:=re.search(r'\bLAYER\s+(\w+)',line):layer=m[1]
  if m:=re.search(r'\bRECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',line):rr.append((layer,*map(float,m.groups())))
 obs[master]=rr
modules=json.loads((O/'cluster_graph.json').read_text())['modules'];cells=next(v['cells']for v in modules.values()if v.get('attributes',{}).get('top') in [1,'1','00000000000000000000000000000001'])
rows=[]
for axis,layer,dim in [('x','M4',1),('y','M5',0)]:
 extent=q['outline_um'][dim];tracks=[.012+.048*i for i in range(math.ceil(extent/.048))if .012+.048*i<extent]
 for cut in q['mandatory_cut_inventory'][axis]:
  pos=cut['position_um'];hard=[];metal=[]
  for n,b in boxes.items():
   amin=b[axis];amax=amin+b['w'if axis=='x'else'h'];orth=b['y'if axis=='x'else'x'];size=b['h'if axis=='x'else'w']
   if amin-.036<=pos<=amax+.036:hard.append((orth-.036,orth+size+.036))
   for ll,x0,y0,x1,y1 in obs[cells[n]['type']]:
    if ll!=layer:continue
    x0+=b['x'];x1+=b['x'];y0+=b['y'];y1+=b['y']
    lo,hi,ol,oh=(x0,x1,y0,y1)if axis=='x'else(y0,y1,x0,x1)
    if lo-.036<=pos<=hi+.036:metal.append((ol-.036,oh+.036))
  def free(intervals):return sum(not any(lo<=t<=hi for lo,hi in intervals)for t in tracks)
  explicit=free(hard);porous=free(metal);bits=cut['mandatory_crossing_unique_driver_bits']
  rows.append({'axis':axis,'signal_layer':layer,'cut_um':pos,'mandatory_unique_driver_bit_lower_bound':bits,'endpoint_joins':cut['mandatory_crossing_bit_joins'],'explicit_channel_tracks':explicit,'OBS_only_free_tracks_diagnostic':porous,'conditional_unique_bit_over_track_ratio':bits/explicit if explicit else None,'screen':'FAIL_NECESSARY_UNIQUE_NET_CUT'if not explicit or bits>.6*explicit else'CONDITIONAL_ONLY','caveat':'Source-driver bit deduplicated across fanout sinks. This is a necessary minimum cut demand, not routed congestion proof. No native parent/PG crossing map exists.'})
r={'status':'CONDITIONAL_EXPLICIT_CHANNEL_CUT_SCREEN','source_geometry':'Q_cooptimized_capsules','tech_lef_sha256':'7694bf4f8ef2f9745e4579f454788a0cf048e8605320f32d1d83ec540ed4ca41','actual_make_tracks_sha256':'4693c8fc81cf9095ed7fba61e778ec81c16c3cadc747f9ce388acf38f8331632','track_contract':{'M4':{'direction':'HORIZONTAL','pitch_um':.048,'offset_um':.012},'M5':{'direction':'VERTICAL','pitch_um':.048,'offset_um':.012},'width_um':.024,'spacing_um':.024,'OBS_center_exclusion_um':.036},'provenance':'Read-only live EPYC4 ORFS container via die_live; not immutable17b image attestation. No M6/M7/M8/M9 parent signal grant.','E_transport_channel_um':1431.624-1028.16,'E_transport_nominal_channel_um':1431.648-1028.16,'E_transport_M5_tracks_upper_bound':math.floor((1431.624-1028.16)/.048),'rows':rows,'limits':['Explicit channel capacity excludes every actual child hard outline; OBS-only porous free space is reported separately and never credited.','Conditional only: die/parent PG crossing map, clock/reset occupancy, actual station leaf outlines and layer assignment remain absent.','Count deduplicates source-driver bits across fanout endpoints for a necessary minimum net cut. No cut closure is claimed.']}
(O/'cut_capacity.json').write_text(json.dumps(r,indent=1)+'\n');print('conditional cuts',len(rows),'flagged',sum(v['screen'].startswith('FAIL')for v in rows),'Echannel',r['E_transport_channel_um'])
