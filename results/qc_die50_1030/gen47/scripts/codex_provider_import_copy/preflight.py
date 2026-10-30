#!/usr/bin/env python3
"""Fail-closed physical/boundary preflight before importing ALL mapped cells."""
import argparse,collections,hashlib,json
from pathlib import Path
from shapely.geometry import box
from shapely.strtree import STRtree

def filehash(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,separators=(',',':'),sort_keys=True).encode()).hexdigest()
def hit(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--mapped',required=True);p.add_argument('--top',default='ot_die_start_stages');p.add_argument('--placements',required=True);p.add_argument('--proposal-constraints',required=True);p.add_argument('--fresh-constraints',required=True);p.add_argument('--bindings',required=True);p.add_argument('--out',required=True);a=p.parse_args();inv=json.load(open(a.inventory));mapped=json.load(open(a.mapped))['modules'][a.top];place=json.load(open(a.placements));old=json.load(open(a.proposal_constraints));fresh=json.load(open(a.fresh_constraints));bindings=json.load(open(a.bindings));issues=collections.Counter();samples=[]
 def issue(code,detail):
  issues[code]+=1
  if len(samples)<100:samples.append(dict(code=code,detail=detail))
 if place['failed']:issue('incomplete_allcell_placement',len(place['failed']))
 if place['inventory_sha256']!=filehash(a.inventory):issue('stale_inventory','placement inventory differs')
 if place['source_constraints_sha256']!=filehash(a.proposal_constraints):issue('proposal_source_mismatch','constraints hash differs')
 if sorted(old['existing_cells'])!=sorted(fresh['existing_cells']):issue('frozen_clock_cells_changed','existing clock/standard-cell geometry differs')
 if not fresh.get('source_odb_sha256'):issue('actual_source_hash_missing','fresh export must pin the actual source ODB')
 if not bindings.get('source_odb_sha256') or bindings.get('source_odb_sha256')!=fresh.get('source_odb_sha256'):issue('boundary_source_mismatch','bindings must reference exact fresh ODB')
 want={c['inst']:c for c in inv['cells']};actual={n:c for n,c in mapped['cells'].items() if c['type']!='$scopeinfo'}
 if set(want)!=set(actual):issue('mapped_inventory_cell_mismatch',dict(missing=len(set(actual)-set(want)),extra=len(set(want)-set(actual))))
 for n,c in want.items():
  y=actual.get(n)
  if y and (c['master']!=y['type'] or c['connections']!=y['connections'] or c['directions']!=y['port_directions']):issue('mapped_cell_contract_mismatch',n)
 rects=[r[2:] for r in fresh['actual_lower_OBS']]+[r[1:] for r in fresh['hard_forbidden']]+[r[2:] for r in fresh['existing_cells']]+[r[2:] for r in fresh['actual_lower_PG']];tree=STRtree([box(*r) for r in rects]);occupied=collections.defaultdict(list);B=4000
 for q in place['cells']:
  r=q['bbox_dbu'];found=[int(i) for i in tree.query(box(*r)) if hit(r,rects[int(i)])]
  if found:issue('actual_source_obstruction_or_keepout',dict(inst=q['inst'],obstacle=rects[found[0]]))
  klist=[(x,y) for x in range(r[0]//B,(r[2]-1)//B+1) for y in range(r[1]//B,(r[3]-1)//B+1)]
  if any(hit(r,t[1]) for k in klist for t in occupied[k]):issue('new_cell_body_overlap',q['inst'])
  for k in klist:occupied[k].append((q['inst'],r))
 ports=mapped['ports'];pb=bindings.get('ports',{});bitnets=collections.defaultdict(set)
 for n,t in ports.items():
  if n not in pb:issue('unbound_native_boundary_port',n);continue
  q=pb[n]
  if len(t['bits'])!=1 or not isinstance(t['bits'][0],int):issue('non_scalar_or_constant_boundary',n);continue
  if not q.get('net') or not q.get('role'):issue('incomplete_boundary_binding',n);continue
  bitnets[t['bits'][0]].add(q['net'])
  if n=='rst_raw_n':issue('global_raw_reset_star_forbidden',n)
 for bit,nets in bitnets.items():
  if len(nets)>1:issue('one_mapped_bit_aliases_distinct_existing_nets',dict(bit=bit,nets=sorted(nets)))
 inputs={b for p in ports.values() if p['direction']=='input' for b in p['bits']};drivers=collections.Counter(b for c in want.values() for p,bs in c['connections'].items() if c['directions'][p]=='output' for b in bs)
 for c in want.values():
  for p,bs in c['connections'].items():
   if len(bs)!=1 or not isinstance(bs[0],int):issue('unmapped_constant_or_non_scalar_cell_port',c['inst']+'/'+p);continue
   if c['directions'][p]=='input' and not drivers[bs[0]] and bs[0] not in inputs:issue('undriven_internal_mapped_bit',dict(inst=c['inst'],pin=p,bit=bs[0]))
 for bit,n in drivers.items():
  if n>1:issue('multiple_internal_mapped_drivers',dict(bit=bit,drivers=n))
 receipt=dict(schema='ot_provider_import_preflight/1',verdict='READY_FOR_REVIEW' if not issues else 'HOLD_NO_IMPORT',source_odb_sha256=fresh.get('source_odb_sha256'),inventory_sha256=filehash(a.inventory),mapped_sha256=filehash(a.mapped),placements_sha256=filehash(a.placements),bindings_sha256=filehash(a.bindings),fresh_constraints_sha256=filehash(a.fresh_constraints),allcells=len(want),issues=dict(issues),samples=samples,scope='Only explicit fresh OBS, all mapped cells and native boundaries; no timing/phase qualification')
 Path(a.out).write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='samples'},indent=2));raise SystemExit(bool(issues))
if __name__=='__main__':main()
