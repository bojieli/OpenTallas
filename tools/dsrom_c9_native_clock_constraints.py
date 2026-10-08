#!/usr/bin/env python3
"""Finite literal-clock contacts for the ONE fixed-graph placement solve.

Track phases come from retained ODB export; extending them to a new parent is
an explicit construction request, not proof of installed parent routing grids.
Only enclosed contacts are admitted here. No M1 extension or inferred CTS.
"""
import gzip,json,math,re
from pathlib import Path
import dsrom_c9_clock_branch_site_binding as B
from dsrom_noECC_hold_station_geometry import rect_move
BASE=B.ROOT/'results/uarch/dsrom_c9_global_native_constraints_20261003'
def overlap(a,b):return min(a[2],b[2])>max(a[0],b[0]) and min(a[3],b[3])>max(a[1],b[1])
def distance(a,b):return max(B.gap(a[0],a[2],b[0],b[2]),B.gap(a[1],a[3],b[1],b[3]))
def shift(box,x,y):return [box[0]+x,box[1]+y,box[2]+x,box[3]+y]
def phases(grid,layer,axis):return sorted({(v[0]%v[2],v[2]) for g in grid['grids'] if g['layer']==layer for v in g[axis]})
def grid_values(lo,hi,sets):
 return sorted({o+i*p for o,p in sets for i in range(math.ceil((lo-o)/p),math.floor((hi-o)/p)+1)})
def native_ports(item,pin,master,grid,spacing=18):
 own=B.pin_rects(item,master,pin);blocked=[]
 for ob in master['OBS']:
  if ob['layer'] in ('M1','M2','M3','V1','V2'):blocked.append(dict(layer=ob['layer'],bbox_DBU=rect_move(ob['bbox_DBU'],item),owner='OBS'))
 for p in master['pins']:
  if p['name']!=pin:
   blocked += [dict(r,owner=p['name']) for r in B.pin_rects(item,master,p['name'])]
 via=grid['tech_via_definitions'];v12=next(v['bbox'] for v in via['VIA12'] if v['layer']=='M1');contacts=[];seen=set()
 for r in own:
  if r['layer']!='M1':continue
  a,b,A,Z=r['bbox_DBU'];lo,hi=a-v12[0],A-v12[2]
  if lo>hi:continue
  # Endpoint X stays enclosed in literal pin; M1 router does not imply a
  # free extension outside the abstract. Finite integer-DBU contacts retain
  # nearest and phase-compatible points for actual M3 horizontal stubs.
  xs=sorted({math.ceil(lo),math.floor(hi),round((lo+hi)/2)}|set(grid_values(lo,hi,phases(grid,'M3','X'))))
  ys=grid_values(b-v12[1],Z-v12[3],phases(grid,'M2','Y'))
  for x in xs:
   for y in ys:
    vx=min(grid_values(x-36,x+36,phases(grid,'M3','X')),key=lambda q:(abs(q-x),q))
    lo2=min(x-14,vx-14);hi2=max(x+14,vx+14)
    if hi2-lo2<38:
     expand=38-(hi2-lo2);lo2-=expand//2;hi2+=expand-expand//2
    shapes=[dict(layer=v['layer'],bbox_DBU=shift(v['bbox'],x,y),via='VIA12') for v in via['VIA12']]
    shapes += [dict(layer=v['layer'],bbox_DBU=shift(v['bbox'],vx,y),via='VIA23') for v in via['VIA23']]
    shapes += [dict(layer='M2',bbox_DBU=[lo2,y-9,hi2,y+9],role='horizontal_access_minarea')]
    shapes += [dict(layer='M3',bbox_DBU=[vx-9,y-19,vx+9,y+19],role='vertical_landing_minarea')]
    reject=[]
    for q in shapes:
     for ob in blocked:
      if q['layer']!=ob['layer']:continue
      # Exact metal overlap and source minimum metal spacing. Cut/EOL/corner
      # and neighboring-cell/global exclusions must be checked by caller.
      if overlap(q['bbox_DBU'],ob['bbox_DBU']) or (q['layer'] in ('M1','M2','M3') and distance(q['bbox_DBU'],ob['bbox_DBU'])<spacing):reject.append(ob['owner'])
    key=x,y,vx
    if not reject and key not in seen:
     seen.add(key);contacts.append(dict(pin_point_DBU=[x,y],M3_endpoint_DBU=[vx,y],shapes=shapes,literal_pin=r['bbox_DBU'],parent_track_phase_installation_required=True))
 # Existing RESETN/SETN ports are already on M2. Enter those literal
 # rectangles through VIA23; do not force a fictitious VIA12/M1 projection.
 for r in own:
  if r['layer']!='M2':continue
  a,b,A,Z=r['bbox_DBU'];lower=next(v['bbox'] for v in via['VIA23'] if v['layer']=='M2')
  xs=grid_values(a-lower[0],A-lower[2],phases(grid,'M3','X'))
  ys=grid_values(b-lower[1],Z-lower[3],phases(grid,'M2','Y'))
  for x in xs:
   for y in ys:
    shapes=[dict(layer=v['layer'],bbox_DBU=shift(v['bbox'],x,y),via='VIA23') for v in via['VIA23']]
    shapes.append(dict(layer='M3',bbox_DBU=[x-9,y-19,x+9,y+19],role='vertical_landing_minarea'))
    if any(q['layer']==ob['layer'] and (overlap(q['bbox_DBU'],ob['bbox_DBU']) or (q['layer'] in ('M1','M2','M3') and distance(q['bbox_DBU'],ob['bbox_DBU'])<spacing)) for q in shapes for ob in blocked):continue
    key=('M2',x,y)
    if key in seen:continue
    seen.add(key);contacts.append(dict(pin_point_DBU=[x,y],M3_endpoint_DBU=[x,y],shapes=shapes,literal_pin=r['bbox_DBU'],native_entry_layer='M2',parent_track_phase_installation_required=True))
 return contacts

def build():
 for r in B.load(BASE/'inputs/origins.json'):
  if B.sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('native source drift')
 grid=B.load(BASE/'inputs/grid.json');tech=gzip.decompress((BASE/'inputs/tech.lef.gz').read_bytes()).decode()
 layer=re.search(r'^LAYER M1\n(.*?)^END M1',tech,re.M|re.S)[1];spacing=round(float(re.search(r'\bSPACING\s+(\S+)\s*;',layer)[1])*1000)
 for name in ('M2','M3'):
  body=re.search(r'^LAYER '+name+r'\n(.*?)^END '+name,tech,re.M|re.S)[1]
  if round(float(re.search(r'\bAREA\s+(\S+)\s*;',body)[1])*1e6)!=666:raise ValueError('source minimum landing area changed')
 lef=B.lef_masters('\n'.join(B.load(B.OLD/'inputs/cell_LEF.json.gz').values()));cases={}
 for master,pin in [(B.BUF,'A'),(B.BUF,'Y'),('DFFHQNx1_ASAP7_75t_R','CLK'),('DFFASRHQNx1_ASAP7_75t_R','CLK'),('DFFASRHQNx1_ASAP7_75t_R','RESETN'),('DFFASRHQNx1_ASAP7_75t_R','SETN')]:
  for orient in ('R0','MX'):
   # 54DBU site phase alternates X modulo36. Source row phase is frozen.
   for x in (0,54):
    item=dict(instance='template',master=master,bbox_DBU=[x,0,x+lef[master]['size_DBU'][0],270],orientation=orient)
    contacts=native_ports(item,pin,lef[master],grid,spacing)
    cases[f'{master}.{pin}.{orient}.x{x}']=dict(contacts=contacts,enclosed_phase_compatible_contact_count=len(contacts))
 result=dict(schema='DS_C9_GLOBAL_SOLVE_FINITE_NATIVE_ENDPOINT_CONSTRAINTS_V1',candidate='DS4096-TP4-S58-PAR2-NP2048',source_grid_sha256=B.sha(BASE/'inputs/grid.json'),source_tech_sha256=B.sha(BASE/'inputs/tech.lef.gz'),M1_min_spacing_DBU=spacing,M2_y_phase_sets=phases(grid,'M2','Y'),M3_x_phase_sets=phases(grid,'M3','X'),cases=cases,physical_build_admitted=False,
   scope='Master-local overlap/min-spacing and literal enclosed VIA12 on retained M2 phase. Full master-neighbor OBS/cuts/EOL/global PG/upper-stack/reset/skew/loading remain global-solve obligations; no M1 extension admitted.',centroid135_is_M2_track=False,new_architecture_parameter=False,new_clock_or_capture_cycles=0)
 (BASE/'model.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v['enclosed_phase_compatible_contact_count'] for k,v in cases.items()},indent=2));return result
if __name__=='__main__':build()
