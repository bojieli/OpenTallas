#!/usr/bin/env python3
"""Mapped native output Q and input first-register reachability, no STA/placement claim."""
import argparse,collections,hashlib,json,pathlib,re
p=argparse.ArgumentParser(description=__doc__);p.add_argument('mapped');p.add_argument('census');p.add_argument('--output',required=True);a=p.parse_args()
data=pathlib.Path(a.mapped).read_bytes();report=json.loads(pathlib.Path(a.census).read_text());m=json.loads(data)['modules'][report['top']];cells=m['cells'];drv={};loads=collections.defaultdict(list)
for n,c in cells.items():
 for pt,bs in c['connections'].items():
  for b in bs:
   if c['port_directions'][pt]=='output':drv[b]=(n,pt)
   else:loads[b].append((n,pt))
def ff(c):return c['type'].startswith(('DFF','SDFF'))
def transparent(c):return bool(re.match(r'^(INV|BUF)',c['type']))
def origin(b):
 if isinstance(b,str):return 'constant',b
 assert b in drv,('undriven',b)
 n,pt=drv[b];c=cells[n]
 if transparent(c):
  ins=[v for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for v in bs];assert len(ins)==1
  return origin(ins[0])
 assert ff(c) and pt in ['Q','QN'],('output not native Q',n,c['type'],pt)
 return n,pt
def first(b,seen=frozenset()):
 assert b not in seen,'combinational loop'
 endpoints=set();depth=0
 for n,pt in loads[b]:
  c=cells[n]
  if ff(c):
   assert pt=='D',('data input reaches non-D sequential pin',n,pt)
   endpoints.add((n,pt));continue
  assert not c['type'].startswith('ot_sram_'),('input reaches macro before register',n,pt)
  for op,bs in c['connections'].items():
   if c['port_directions'][op]=='output':
    for ob in bs:
     ep,dep=first(ob,seen|{b});endpoints.update(ep);depth=max(depth,dep+1)
 return endpoints,depth
out={};inp={};excluded=[]
for n,port in m['ports'].items():
 if n.startswith('app_'):
  excluded.append(n);continue # Internal taps: central core is inside APPLICATION hard boundary.
 if port['direction']=='output':out[n]=[list(origin(b))for b in port['bits']]
 elif n not in ['clk','rst_n']:
  vals=[]
  for b in port['bits']:
   ep,depth=first(b)
   vals.append({'first_DFF_count':len(ep),'max_comb_cell_depth_before_first_DFF':depth})
  inp[n]=vals
proof={'top':report['top'],'status':'MAPPED_REGISTER_REACHABILITY_PASS_NOT_STA_OR_PHYSICAL_APPROVAL','outputs':out,'inputs':inp,'excluded_internal_core_taps':excluded,'input_interpretation':'Bank token metadata enters selected4slot ring storage through write muxes; input reachability is not a zero-logic timing assertion. All such normal single-edge paths need TT/FF native pin timing and legal placement.','mapped_sha256':hashlib.sha256(data).hexdigest(),'source_sha256':report['source_sha256']}
pathlib.Path(a.output).write_text(json.dumps(proof,indent=2)+'\n');print(report['top'],'outputs Q/constant PASS; max input logic',max(x['max_comb_cell_depth_before_first_DFF']for v in inp.values()for x in v))
