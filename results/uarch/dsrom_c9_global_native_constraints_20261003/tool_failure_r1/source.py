#!/usr/bin/env python3
"""Full frozen-problem native contact filter, not a second placement solve."""
import copy,json,math
from collections import defaultdict
import dsrom_c9_native_clock_constraints as N
B=N.B;BASE=N.BASE

def neighbors_index(cells):
 index=defaultdict(list)
 for i,p in enumerate(cells):
  a,b,A,Z=p['bbox_DBU']
  for x in range(a//540,(A-1)//540+1):
   for y in range(b//270,(Z-1)//270+1):index[x,y].append(i)
 return index

def audit():
 grid=B.load(BASE/'inputs/grid.json');lef=B.lef_masters('\n'.join(B.load(B.OLD/'inputs/cell_LEF.json.gz').values()));template=N.B.load(BASE/'model.json');cases={}
 for s in ('0','1'):
  problem=B.load(BASE/f'inputs/global_shard{s}_problem.json.gz');original=B.lines(B.OLD/f'shard{s}_cells.jsonl.gz')
  hook=[dict(p,instance=p.get('proposed_instance',p.get('instance'))) for p in problem['hook']]
  identity=[dict(p,instance=p.get('proposed_instance',p.get('instance'))) for p in problem['identity']]
  cells=original+hook+identity;byname={p['instance']:p for p in cells};idx=neighbors_index(cells);blocked={};cache={}
  def cell_exclusions(i):
   if i not in blocked:
    p=cells[i];m=lef[p['master']];q=[dict(layer=r['layer'],bbox_DBU=N.rect_move(r['bbox_DBU'],p),owner=p['instance']) for r in m['OBS'] if r['layer'] in ('M1','M2','M3','V1','V2')]
    for pin in m['pins']:q += [dict(r,owner=p['instance']) for r in B.pin_rects(p,m,pin['name']) if r['layer'] in ('M1','M2','M3','V1','V2')]
    blocked[i]=q
   return blocked[i]
  def contacts(p,pin):
   x,y=p['bbox_DBU'][:2];phase=x%36;key=(p['master'],pin,p['orientation'],phase)
   if key not in cache:
    probe=dict(p,bbox_DBU=[phase,0,phase+lef[p['master']]['size_DBU'][0],270]);cache[key]=N.native_ports(probe,pin,lef[p['master']],grid)
   out=[]
   for c in cache[key]:
    q=copy.deepcopy(c);q['pin_point_DBU']=[c['pin_point_DBU'][0]+x-phase,c['pin_point_DBU'][1]+y];q['M3_endpoint_DBU']=[c['M3_endpoint_DBU'][0]+x-phase,c['M3_endpoint_DBU'][1]+y]
    for r in q['shapes']:r['bbox_DBU']=N.shift(r['bbox_DBU'],x-phase,y)
    out.append(q)
   return out
  def surviving(p,pin):
   x,y,X,Y=p['bbox_DBU'];near={i for xx in range((x-54)//540,(X+53)//540+1) for yy in range((y-54)//270,(Y+53)//270+1) for i in idx.get((xx,yy),[]) if cells[i]['instance']!=p['instance']}
   obs=[r for i in near for r in cell_exclusions(i)];mask=0;options=contacts(p,pin)
   for j,c in enumerate(options):
    conflict=False
    for r in c['shapes']:
     for o in obs:
      if r['layer']!=o['layer']:continue
      # Supplies on adjacent boundaries are covered once as exact polygons.
      if N.overlap(r['bbox_DBU'],o['bbox_DBU']) or (r['layer'] in ('M1','M2','M3') and N.distance(r['bbox_DBU'],o['bbox_DBU'])<18):conflict=True;break
     if conflict:break
    if not conflict:mask|=1<<j
   return mask,len(options)
  masks=[];missing=[];roots={};native_owner={}
  for n in B.lines(B.OLD/f'shard{s}_clock_nets.jsonl.gz'):
   for port in [n['source']]+n['sinks']:native_owner[port['instance'],port['pin']]=port
  for p in hook+identity:
   if p['master']=='DFFASRHQNx1_ASAP7_75t_R':
    for pin in ('CLK','RESETN','SETN'):native_owner[p['instance'],pin]=None
  for (name,pin),port in sorted(native_owner.items()):
   p=byname[name];mask,n=surviving(p,pin)
   if not mask:missing.append(dict(instance=name,pin=pin,master=p['master'],own_master_native_options=n))
   if name==problem['source_root_input']['instance']:roots[pin]=dict(mask=mask,options=n,contacts=contacts(p,pin))
  # Exact full site pool: masks index the native master templates, while
  # original/site identities and complete branch/pad topology stay frozen.
  for i,site in enumerate(problem['sites']):
   p=dict(site,instance=site['proposed_site_ID']);a,na=surviving(p,'A');y,ny=surviving(p,'Y');masks.append(dict(site=i,A_mask=a,Y_mask=y,A_options=na,Y_options=ny))
  artifact=BASE/f'shard{s}_full_native_site_masks.jsonl.gz';B.dumpgz(artifact,masks)
  f=BASE/f'shard{s}_original_native_contact_failures.jsonl.gz';B.dumpgz(f,missing)
  cases[s]=dict(frozen_problem_sha256=B.sha(BASE/f'inputs/global_shard{s}_problem.json.gz'),original_and_hook_identity_cells=len(cells),actual_clock_reset_pin_owners=len(native_owner),owners_without_neighbor_clear_native_contact=len(missing),source_root_native_contacts=roots,
   source_slot_sites=len(masks),sites_with_both_native_A_Y=sum(bool(p['A_mask']) and bool(p['Y_mask']) for p in masks),sites_without_native_A=sum(not p['A_mask'] for p in masks),sites_without_native_Y=sum(not p['Y_mask'] for p in masks),site_masks_sha256=B.sha(artifact),original_failure_sha256=B.sha(f),baseline_unplaced_common_control_not_excluded=True,
   full_reset_clock_waveforms_global_upper_stack_PG_supply_current_and_route_EOLOBS_not_qualified=True)
  print(s,{k:v for k,v in cases[s].items() if k!='source_root_native_contacts'},flush=True)
 result=dict(schema='DS_C9_FULL_FROZEN_GLOBAL_NATIVE_CONTACT_FILTER_V1',source_global_problem_commit='e13772e074b8acae0552a275dc08b3b06299c00d',candidate='DS4096-TP4-S58-PAR2-NP2048',source_native_template_sha256=B.sha(BASE/'model.json'),source_graph_and_counts_unchanged=True,second_solver_launched=False,physical_build_admitted=False,cases=cases,
  scope='Complete original/hook/identity neighbor pin/OBS overlap and minimum metal spacing through M3 for the exact full legal site pool. Cut/EOL/corner rules, mutual chosen-candidate escapes, upper layers, field/service OBS, supply and reset/clock waveforms still require the single shared solver/context join.')
 (BASE/'global_join.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');return result
if __name__=='__main__':audit()
