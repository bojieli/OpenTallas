#!/usr/bin/env python3
"""Audit one frozen c9 assignment: literal PG and enclosed VIA12 lower bound.

No routed, extracted, global-skew, upper-stack or power-current claim. A failure
rejects the enclosed-contact construction, not all possible legal M1 extensions.
"""
import json,sys,copy
from pathlib import Path
import dsrom_c9_clock_branch_site_binding as g
BASE=g.BASE
HOLD=g.ROOT/'results/uarch/dsrom_noECC_hold_station_geometry_20261002/model.json'
def contains(a,b):return a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]
def contact_centers(rects,via):
 result=[]
 for r in rects:
  if r['layer']!='M1':continue
  a,b,A,B=r['bbox_DBU'];x,y,X,Y=via
  q=[a-x,b-y,A-X,B-Y]
  if q[0]<=q[2] and q[1]<=q[3]:result.append(dict(layer='M1_contact_centers',bbox_DBU=q))
 return result

def audit():
 source=g.load(BASE/'model.json');old=g.load(g.OLD/'model.json');hold=g.load(HOLD)
 lef=g.lef_masters('\n'.join(g.load(g.OLD/'inputs/cell_LEF.json.gz').values()))
 via=next(v['bbox_DBU'] for v in hold['physical_native_via_templates']['VIA12'] if v['layer']=='M1');C=g.load(g.CUT/'inputs/model.json')['restricted_route_family_RC_fF_per_um'];cases={}
 for s in ('0','1'):
  cells=g.lines(BASE/f'shard{s}_assigned_cells.jsonl.gz');original=g.lines(g.OLD/f'shard{s}_cells.jsonl.gz');edges=g.lines(BASE/f'shard{s}_assigned_edges.jsonl.gz');patch=source['cases'][s]['common_prefix_patch_DBU']
  rails=copy.deepcopy(old['physical_shards'][s]['PG_M1_literal_rails']);extra=0
  for r in rails:
   y=(r['bbox_DBU'][1]+r['bbox_DBU'][3])/2
   if patch[1]<=y<=patch[3]:
    end=max(r['bbox_DBU'][2],patch[2]);extra+=(end-r['bbox_DBU'][2])*(r['bbox_DBU'][3]-r['bbox_DBU'][1]);r['bbox_DBU'][2]=end
  rows={int((r['bbox_DBU'][1]+r['bbox_DBU'][3])/2):r for r in rails};missing=[]
  for p in cells:
   for supply in ('VDD','VSS'):
    for pin in g.pin_rects(p,lef[p['master']],supply):
     b=pin['bbox_DBU'];rail=rows.get(int((b[1]+b[3])/2))
     if rail is None or rail['net']!=supply or rail['layer']!=pin['layer'] or not contains(rail['bbox_DBU'],b):missing.append([p['instance'],supply,b])
  occupancy={};collisions=[]
  for p in original+cells:
   a,b,A,B=p['bbox_DBU'];occupancy.setdefault((b,B),[]).append((a,A,p['instance']))
  for key,intervals in occupancy.items():
   last=None
   for interval in sorted(intervals):
    if last is not None and interval[0]<last[1]:collisions.append([last[2],interval[2],key])
    if last is None or interval[1]>last[1]:last=interval
  failures=[];no_contact=0;worst=None
  for e in edges:
   a=contact_centers(e['source']['literal_rectangles'],via);b=contact_centers(e['sink']['literal_rectangles'],via)
   cap=g.literal_cap(a,b,C) if a and b else None
   if cap is None or cap>e['metal_budget_fF']+1e-8:
    r=dict(branch_net=e['branch_net'],destination=e['destination'],ordinal=e['ordinal'],budget_fF=e['metal_budget_fF'],enclosed_VIA12_M8_M9_lower_bound_fF=cap,source=e['source']['instance'],sink=e['sink']['instance'])
    failures.append(r)
    if cap is None:no_contact+=1
    elif worst is None or cap-r['budget_fF']>worst['enclosed_VIA12_M8_M9_lower_bound_fF']-worst['budget_fF']:worst=r
  f=BASE/f'shard{s}_enclosed_VIA12_failures.jsonl.gz';g.dumpgz(f,failures)
  cases[s]=dict(assigned_BUF=len(cells),primitive_count_including_original=len(original)+len(cells),fixed_height_row_overlap_pairs=collisions,literal_M1_supply_missing=missing,
   PG_M1_literal_rails=rails,new_local_rail_metal_area_um2=extra/1e6,PG_rail_extension_not_new_cell_area=True,
   checked_assigned_edges=len(edges),enclosed_VIA12_failures=len(failures),no_enclosed_contact_edges=no_contact,worst_enclosed_VIA12_bound_failure=worst,failure_artifact_sha256=g.sha(f),
   common_prefix_control_instance_union_not_complete=True,native_upper_stack_track_OBS_and_crossnet_routes_not_built=True,PG_upfeed_current_IR_EM_not_qualified=True)
 result=dict(schema='DS_C9_ONE_ASSIGNED_GRAPH_NATIVE_CONTACT_PG_AUDIT_V1',source_assignment_sha256=g.sha(BASE/'model.json'),source_hold_via_model_sha256=g.sha(HOLD),source_VIA12=hold['physical_native_via_templates']['VIA12'],candidate=source['candidate'],cases=cases,
  physical_build_admitted=False,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,actual_root_skew_and_reset_release_qualified=False,
  scope='Enclosed literal VIA12 contacts and local M1 rails only; no metal-extension/native-route impossibility or timing signoff claim.',added_BUF=0,annex_charge_mm2=0)
 (BASE/'access_model.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps({s:{k:v for k,v in c.items() if k not in ('PG_M1_literal_rails','literal_M1_supply_missing')} for s,c in cases.items()},indent=2));return result
if __name__=='__main__':audit()
