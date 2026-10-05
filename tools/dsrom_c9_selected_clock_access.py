#!/usr/bin/env python3
"""Necessary first-hop access checks for the selected c9 relay/site inventory.

Optimistic literal-pin distances exclude all vias, access detours, PG/OBS and
other-net conflicts. A failed lower bound rejects this inventory assignment,
not the candidate architecture or a distributed inventory of the same size.
"""
import bisect,gzip,hashlib,json
from pathlib import Path
from dsrom_noECC_production_context import lef_masters
from dsrom_noECC_hold_station_geometry import pin_rects
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_c9_selected_clock_access_20261003'
PRIOR=ROOT/'results/uarch/dsrom_R49_raw_physical_union_20261002'
BUF='BUFx4_ASAP7_75t_R'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
 p=BASE/'inputs'/name;raw=p.read_bytes();return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
def gap(a,A,b,B):return max(0,b-A,a-B)
def nearest_pin_lower_bound(source_rects,rows,C,row_x=None):
 best=None
 for source in source_rects:
  a,b,A,B=source['bbox_DBU']
  for (y,Y,width),items in rows.items():
   xs=row_x[(y,Y,width)] if row_x is not None else [v[0] for v in items];i=bisect.bisect_left(xs,a)
   for j in (i-1,i):
    if not 0<=j<len(items):continue
    x,name=items[j];dx=gap(a,A,x,x+width);dy=gap(b,B,y,Y)
    value=(dx*C['M8']+dy*C['M9'])/1000
    if best is None or value<best['optimistic_M8_M9_metal_C_fF']:
     best=dict(site=name,optimistic_M8_M9_metal_C_fF=value,L1_lower_bound_um=(dx+dy)/1000,
      source_Y_literal_rect_DBU=[a,b,A,B],nearest_A_literal_rect_DBU=[x,y,x+width,Y])
 return best

def build():
 origins=load('origins.json')
 for r in origins:
  if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('selected source drift')
 c=load('model.json');lef=lef_masters('\n'.join(json.loads(gzip.decompress((PRIOR/'inputs/cell_LEF.json.gz').read_bytes())).values()));cases={}
 for shard in (0,1):
  sites=load(f'shard{shard}_correction_sites.json.gz');branches=load(f'shard{shard}_clock_branches.json.gz')
  nets={n['name']:n for n in [json.loads(v) for v in gzip.decompress((PRIOR/f'shard{shard}_clock_nets.jsonl.gz').read_bytes()).decode().splitlines()]}
  rows={}
  for p in sites:
   p=dict(p,instance=p['proposed_site_ID'])
   for rect in pin_rects(p,lef[BUF],'A'):
    a,b,A,B=rect['bbox_DBU'];rows.setdefault((b,B,A-a),[]).append((a,p['instance']))
  for values in rows.values():values.sort()
  raw=json.loads((PRIOR/'model.json').read_text())['physical_shards'][str(shard)]['raw_slot_bbox_DBU']
  failures=[];checked=0;worst=None;raw_cut=[];nearest_cache={};row_x={key:[v[0] for v in items] for key,items in rows.items()}
  for branch in branches:
   if branch['proposed_relay_BUF']==0:continue
   checked+=1;n=nets[branch['net']]
   if branch['net'] not in nearest_cache:nearest_cache[branch['net']]=nearest_pin_lower_bound(n['source']['literal_rectangles'],rows,c['restricted_route_family_RC_fF_per_um'],row_x)
   near=nearest_cache[branch['net']]
   budget=branch['first_driver_total_wire_budget_fF']/2/branch['source_fanout']
   a,b,A,B=raw;C=c['restricted_route_family_RC_fF_per_um']
   any_raw_lower=min((gap(r['bbox_DBU'][0],r['bbox_DBU'][2],a,A)*C['M8']+gap(r['bbox_DBU'][1],r['bbox_DBU'][3],b,B)*C['M9'])/1000 for r in n['source']['literal_rectangles'])
   if any_raw_lower>budget:raw_cut.append(dict(net=branch['net'],source=branch['source'],destination=branch['destination'],first_branch_metal_budget_fF=budget,optimistic_C_to_any_point_in_raw_rectangle_fF=any_raw_lower))
   if near['optimistic_M8_M9_metal_C_fF']>budget:
    f=dict(net=branch['net'],source=branch['source'],destination=branch['destination'],source_fanout=branch['source_fanout'],
      first_branch_metal_budget_fF=budget,source_contact_stub_budget_preserved=True,**near)
    failures.append(f)
    if worst is None or f['optimistic_M8_M9_metal_C_fF']-budget>worst['optimistic_M8_M9_metal_C_fF']-worst['first_branch_metal_budget_fF']:worst=f
  artifact=BASE/f'shard{shard}_first_hop_deficits.json.gz';artifact.write_bytes(gzip.compress((json.dumps(failures,sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
  source_ys=[p['bbox_DBU'][1] for p in sites]
  cases[str(shard)]=dict(selected_correction_site_count=len(sites),raw_bbox_DBU=raw,selected_site_y_range_DBU=[min(source_ys),max(source_ys)],
    relay_branches_checked=checked,branches_with_no_first_hop_site_inside_selected_metal_budget=len(failures),
    worst_first_hop_deficit=worst,artifact_sha256=sha(artifact),one_to_one_assignment_not_attempted_if_necessary_bound_fails=True)
  cases[str(shard)].update(first_relay_branches_that_cannot_use_ANY_raw_rectangle_site_under_current_budget=len(raw_cut),raw_only_first_hop_cut_witnesses=raw_cut,
    minimum_first_relay_BUF_sites_outside_raw_rectangle_at_unchanged_source_graph=len(raw_cut),
    minimum_buffer_body_to_relocate_outside_raw_um2=len(raw_cut)*lef[BUF]['size_DBU'][0]*lef[BUF]['size_DBU'][1]/1e6,additional_BUF_count=0,
    repair='Redistribute existingselectedcount acrossallrawrows andbindtheseoutside-rawfirsthopsnearupperparents; commonowner/sites/PGmustbeexplicit. No newbank/count or totalreticlearea inference.')
 result=dict(schema='DS_C9_SELECTED_CLOCK_LITERAL_FIRST_HOP_NECESSARY_ACCESS_V1',candidate=c['candidate'],source_origins=origins,
  selected_source_commit=origins[0]['commit'],selected_selector_bank=c['selected_selector_clock_construction'],
  prior51ae_annex_charge_mm2=0,no_new_bank_or_buffer_count=True,additional_bank_or_cells=0,shards=cases,
  source_relay_and_pad_count=c['positive_new_relay_and_pad_BUF'],source_627_minimum_extra_retained=True,
  source_1483_control_plus46_new_clock_reset_and169_identity_union_not_qualified=True,
  rejection_scope='Selected finite correction-site list and its declaredM8/M9first-hopbudget only. Full availableemptyMXrows may support a redistributedlist at unchangedcounts; no architecture impossibility claim.',
  next_required_construction='Assign selectedrelay/padbranches to distributedlegalMXsites near sourceANDsink underfirsthop2.88/kmetalbudget, then nativevia/PG/OBS and sourceclock/reset/loadedSSFF. Existing top-first site list cannot be treated as connected.',
  physical_build_admitted=False,clock_reset_PG_or_escape_qualified=False,actual_consumer_deadline_not_supplied=True,new_jobs=[])
 (BASE/'model.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(cases,indent=2));return result
if __name__=='__main__':build()
