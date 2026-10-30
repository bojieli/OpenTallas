#!/usr/bin/env python3
"""Project exact native LEF pins for joint PG PREBUILD; never claim actual ODB.
Mixed clock and provider rails retain their actual offsets/master/orientation.
"""
import argparse,collections,json,math
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree
p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--placements',required=True);p.add_argument('--constraints',required=True);p.add_argument('--old-clock-terms',required=True);p.add_argument('--out',required=True);a=p.parse_args();inv=json.load(open(a.inventory));pl=json.load(open(a.placements));g=json.load(open(a.constraints));old=json.load(open(a.old_clock_terms));assert not pl['failed'];D=pl['dbu'];loc={c['inst']:c for c in pl['cells']};terms=[];signal=[];instances=[]
for c in inv['cells']:
 q=loc[c['inst']];assert q['orient']=='R0';x,y=q['xy_dbu'];m=g['masters'][c['master']];instances.append(dict(inst=q['odb_inst'],mapped_inst=c['inst'],master=c['master'],stage=c['stage'],role=c.get('role','origin'),orient=q['orient'],bbox_dbu=q['bbox_dbu']))
 for pin,pd in m['pins'].items():
  rr=[[ly,x+x0,y+y0,x+x1,y+y1] for ly,x0,y0,x1,y1 in pd['rects_dbu']]
  if pd['sigtype'] in ['POWER','GROUND']:
   terms.append(dict(inst=q['odb_inst'],mapped_inst=c['inst'],master=c['master'],orient=q['orient'],pin=pin,connected_net='VDD' if pd['sigtype']=='POWER' else 'VSS',shapes_dbu=rr,geometry_kind='PROJECTED_ACTUAL_LEF'))
  else:
   for ly,*r in rr:signal.append([q['odb_inst'],pin,ly,*r])
combined=old['terms']+terms;by=collections.defaultdict(list);rows=collections.defaultdict(list);unsupported=[];outside=[]
for t in combined:
 if t['orient']!='R0' or len(t['shapes_dbu'])!=1 or t['shapes_dbu'][0][0]!='M1' or t['shapes_dbu'][0][4]-t['shapes_dbu'][0][2]!=18:unsupported.append([t['inst'],t['pin'],t['orient'],t['shapes_dbu']])
 for ly,*r in t['shapes_dbu']:
  by[t['pin'],ly].append((t['inst'],r));rows[t['pin'],ly,r[1],r[3]].append((r[0],r[2]))
  if r[0]<g['die_dbu'][0] or r[1]<g['die_dbu'][1] or r[2]>g['die_dbu'][2] or r[3]>g['die_dbu'][3]:outside.append([t['inst'],t['pin'],ly,*r])
contacts=[]
for ly in {k[1] for k in by}:
 pp=by['VDD',ly];nn=by['VSS',ly];tree=STRtree([box(*r) for _,r in nn])
 for n,r in pp:
  for j in tree.query(box(*r)):
   v,s=nn[int(j)];dx=min(r[2],s[2])-max(r[0],s[0]);dy=min(r[3],s[3])-max(r[1],s[1])
   if dx>=0 and dy>=0 and (dx>0 or dy>0):contacts.append([n,v,ly,dx,dy])
groups=[]
for (net,ly,y0,y1),rr in rows.items():
 rr.sort();run=None
 for x0,x1 in rr:
  if run and x0<=run[1]:run[1]=max(run[1],x1)
  else:
   if run:groups.append((net,ly,run[0],y0,run[1],y1))
   run=[x0,x1]
 if run:groups.append((net,ly,run[0],y0,run[1],y1))
empty50=[]
for n,ly,x0,y0,x1,y1 in groups:
 if ly!='M1':continue
 parity=0 if n=='VDD' else 1;base=32+64*parity
 if math.ceil((x0+50-base)/128)>math.floor((x1-50-base)/128):empty50.append([n,x0,y0,x1,y1])
out=Path(a.out);out.mkdir(parents=True,exist_ok=True);json.dump(dict(schema='ot_projected_provider_pins/1',geometry_kind='PROJECTED_ACTUAL_LEF_AT_PROPOSED_LEGAL_POSITIONS',actual_ODB_bound=False,dbu=D,instances=instances,terms=terms,signal_shapes=signal),open(out/'provider_pin_geometry.json','w'),separators=(',',':'));json.dump(dict(dbu=D,geometry_kind='ACTUAL_OLD_CLOCK_PLUS_PROJECTED_PROVIDER',actual_ODB_bound=False,terms=combined),open(out/'combined_power_terms.json','w'),separators=(',',':'))
summary=dict(provider_cells=len(instances),new_pg_terms=len(terms),combined_pg_terms=len(combined),new_signal_pin_rects=len(signal),orientations=dict(collections.Counter(t['orient'] for t in terms)),new_pg_shape_counts=dict(collections.Counter(str([(r[0],r[4]-r[2]) for r in t['shapes_dbu']]) for t in terms)),opposing_native_rail_contacts=len(contacts),unsupported_native_geometry=len(unsupported),native_shapes_outside_die=len(outside),merged_rail_groups=len(groups),groups_without_old_50nm_margin_128nm_grid_slot=len(empty50),scope='Projected prebuild only; fresh actual ODB pin readback required')
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');json.dump(dict(opposing_contacts=contacts,unsupported=unsupported,outside_die=outside,no_old_50nm_grid_slot=empty50),open(out/'findings.json','w'),separators=(',',':'));print(json.dumps(summary,indent=2))
