#!/usr/bin/env python3
"""Actual LEF pin-bbox registered reach of the complete mapped provider graph.
Boundary bits without an explicit native source binding are UNRESOLVED, never
zero-distance. Clock pins are recorded separately for the loaded-clock owner.
"""
import argparse,collections,json
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--inventory',required=True);p.add_argument('--placements',required=True);p.add_argument('--constraints',required=True);p.add_argument('--limit-um',type=float,default=405);p.add_argument('--out',required=True);a=p.parse_args();inv=json.load(open(a.inventory));place=json.load(open(a.placements));g=json.load(open(a.constraints));assert not place['failed'];D=g['dbu'];cells={c['inst']:c for c in inv['cells']};loc={c['inst']:c for c in place['cells']};drivers=collections.defaultdict(list)
 for c in cells.values():
  for pin,bits in c['connections'].items():
   if c['directions'][pin]=='output':
    for bit in bits:drivers[bit].append((c['inst'],pin))
 multi={str(b):v for b,v in drivers.items() if len(v)!=1};assert not multi,'multiple actual mapped drivers'
 cache={};active=set();boundary=set()
 def source(bit):
  if bit in cache:return cache[bit]
  if bit in active:raise ValueError('combinational loop at bit '+str(bit))
  if bit not in drivers:boundary.add(bit);return {('BOUNDARY',str(bit))}
  active.add(bit);n,pin=drivers[bit][0];c=cells[n]
  if c['sequential']:out={(n,pin)}
  else:
   out=set()
   for p,bs in c['connections'].items():
    if c['directions'][p]=='input':
     for b in bs:out.update(source(b))
  active.remove(bit);cache[bit]=out;return out
 def pinbox(n,p):
  c=cells[n];q=loc[n];assert q['orient']=='R0';rr=g['masters'][c['master']]['pins'][p]['rects_dbu'];assert rr,'actual LEF signal pin has no shape';x,y=q['xy_dbu'];return [x+min(r[1] for r in rr),y+min(r[2] for r in rr),x+max(r[3] for r in rr),y+max(r[4] for r in rr)]
 def dist(r,s):return max(abs(x-u)+abs(y-v) for x in [r[0],r[2]] for y in [r[1],r[3]] for u in [s[0],s[2]] for v in [s[1],s[3]])/D
 arcs=[];unresolved=[];clocks=[]
 for c in cells.values():
  if not c['sequential']:continue
  for pin,bs in c['connections'].items():
   if c['directions'][pin]!='input':continue
   if pin=='CLK':clocks.append(dict(inst=c['inst'],pin=pin,bits=bs,bbox_dbu=pinbox(c['inst'],pin)));continue
   for bit in bs:
    for n,p in source(bit):
     if n=='BOUNDARY':unresolved.append(dict(dst_inst=c['inst'],dst_pin=pin,source_bit=p));continue
     d=dist(pinbox(n,p),pinbox(c['inst'],pin));arcs.append(dict(src_inst=n,src_pin=p,dst_inst=c['inst'],dst_pin=pin,um=d,over=d>a.limit_um+1e-9))
 arcs.sort(key=lambda q:-q['um']);result=dict(scope='All mapped FF/comb registered reach; external native boundary bindings still required; no timing/phase gate',registered_arcs=len(arcs),over_limit=sum(q['over'] for q in arcs),max_um=arcs[0]['um'] if arcs else 0,limit_um=a.limit_um,boundary_unresolved_arcs=len(unresolved),boundary_unresolved_bits=len(boundary),clock_pins=len(clocks),arcs=arcs,unresolved=unresolved,clocks=clocks,verdict='DIAGNOSTIC_REACH_FAIL' if any(q['over'] for q in arcs) else 'DIAGNOSTIC_INTERNAL_REACH_PASS_BOUNDARIES_PENDING');Path(a.out).write_text(json.dumps(result,separators=(',',':'))+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['arcs','unresolved','clocks']},indent=2))
if __name__=='__main__':main()
